# src/services/quiz_session_service.py
"""
Quiz Session Scoring Engine -- Day 12
Idempotency, Locking, State Finalization

Three sections:
  A. Pure scoring functions (no DB, no HTTP -- unit-testable)
  B. Question-fetching helper (calls question-management-service)
  C. QuizSessionService class (orchestrates the quiz lifecycle)
"""

import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.quiz_session import QuizSession, SessionStatus
from src.models.test_submission import TestSubmission, SubmissionStatus
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.quiz_session_schema import (
    QuizSessionCreate,
    DraftSaveIn,
    PartASubmitIn,
    PartBSubmitIn,
    QuizSubmitOut,
    PartAQuestionsOut,
    PartBQuestionsOut,
    QuizQuestionOut,
    QuizOptionOut,
    SessionStatusOut,
    PartAConfig,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section A -- Pure scoring functions
# ---------------------------------------------------------------------------

def score_exact_match(selected: list, correct: int) -> float:
    """MCQ single-select or True/False: 1.0 if exact match."""
    return 1.0 if len(selected) == 1 and selected[0] == correct else 0.0


def score_jaccard(selected: list, correct: list) -> float:
    """Multi-select partial credit via Jaccard similarity."""
    if not correct:
        return 1.0 if not selected else 0.0
    s, c = set(selected), set(correct)
    union = s | c
    return len(s & c) / len(union) if union else 1.0


def score_question(
    question_type: str,
    selected: list,
    correct_answer,
    correct_answers,
) -> float:
    """Dispatch to correct scoring algorithm based on question_type."""
    if question_type in ("mcq", "true_false"):
        if correct_answer is None:
            return 0.0
        return score_exact_match(selected, correct_answer)
    elif question_type == "multi":
        return score_jaccard(selected, correct_answers or [])
    return 0.0


def score_part(stored_questions: list, answers: list) -> tuple:
    """
    Score all answers for one part.
    Returns (correct_count: float, percentage: float 0-100).
    correct_count can be fractional due to Jaccard partial credit.
    """
    answer_map = {a["question_id"]: a["selected_answers"] for a in answers}
    correct_count = 0.0
    for q in stored_questions:
        selected = answer_map.get(q["question_id"], [])
        pts = score_question(
            q["question_type"],
            selected,
            q.get("correct_answer"),
            q.get("correct_answers"),
        )
        correct_count += pts
    total = len(stored_questions)
    pct = round(correct_count / total * 100, 2) if total > 0 else 0.0
    return correct_count, pct


# ---------------------------------------------------------------------------
# Section B -- Question-fetching helper
# ---------------------------------------------------------------------------

async def fetch_questions_for_part(
    question_service_url: str,
    test_id: int,
    config: dict,
    exclude_ids: list,
) -> list:
    """
    Fetch questions from question-management-service and sample by difficulty.

    Calls GET {question_service_url}/v1/api/questions/?limit=200
    Filters by difficulty, excludes already-seen question IDs, samples randomly.
    Raises HTTPException 503 if service is unreachable or questions lack answer fields.
    """
    if not question_service_url:
        logger.warning("QUESTION_SERVICE_URL not configured — returning empty question list")
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{question_service_url}/v1/api/questions/",
                params={"limit": 200},
            )
    except httpx.RequestError as exc:
        logger.error("Question service unreachable: %s", exc)
        raise HTTPException(status_code=503, detail="Question service unavailable")

    if response.status_code != 200:
        logger.error(
            "Question service returned %s: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(status_code=503, detail="Question service unavailable")

    raw_questions = response.json()
    if not isinstance(raw_questions, list):
        # Some services wrap in {"items": [...]} or {"data": [...]}
        raw_questions = (
            raw_questions.get("items")
            or raw_questions.get("data")
            or raw_questions.get("questions")
            or []
        )

    exclude_set = set(exclude_ids)
    selected_questions = []

    for difficulty, count in config.items():
        pool = [
            q for q in raw_questions
            if (
                q.get("difficulty") == difficulty
                and str(q.get("id") or q.get("_id") or "") not in exclude_set
                and q.get("type") in ("mcq", "multi", "true_false")
            )
        ]
        # Validate answer fields are present
        valid_pool = []
        for q in pool:
            if q.get("type") in ("mcq", "true_false"):
                if q.get("correct_answers") is None and q.get("correct_answer") is None:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Question service returned question without correct_answer "
                            "(id={})".format(q.get("id") or q.get("_id"))
                        ),
                    )
            elif q.get("type") == "multi":
                if not q.get("correct_answers"):
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Question service returned multi-select question without "
                            "correct_answers (id={})".format(q.get("id") or q.get("_id"))
                        ),
                    )
            valid_pool.append(q)

        sampled = random.sample(valid_pool, min(count, len(valid_pool)))
        selected_questions.extend(sampled)

    return selected_questions


def _normalize_question(raw: dict) -> dict:
    """
    Convert a raw question from question-management-service to the internal
    storage format used in part_a / part_b JSON blobs.
    """
    q_id = str(raw.get("id") or raw.get("_id") or str(uuid.uuid4()))
    q_type = raw.get("type", "mcq")

    # Normalise correct_answer for mcq/true_false
    correct_answer = raw.get("correct_answer")
    correct_answers_raw = raw.get("correct_answers")

    if q_type in ("mcq", "true_false") and correct_answer is None and correct_answers_raw:
        correct_answer = correct_answers_raw[0] if correct_answers_raw else None

    correct_answers = None
    if q_type == "multi":
        correct_answers = correct_answers_raw or []

    # Build options list
    raw_options = raw.get("options") or []
    options = []
    for i, opt in enumerate(raw_options):
        if isinstance(opt, dict):
            options.append({"option_id": opt.get("option_id", i), "text": opt.get("text", "")})
        else:
            options.append({"option_id": i, "text": str(opt)})

    return {
        "question_id": q_id,
        "question_text": raw.get("question_text", ""),
        "question_type": q_type,
        "difficulty": raw.get("difficulty", "medium"),
        "options": options,
        "correct_answer": correct_answer,
        "correct_answers": correct_answers,
    }


def _safe_question_out(q: dict) -> QuizQuestionOut:
    """Convert internal question dict to safe client-facing schema (no answers)."""
    options = [
        QuizOptionOut(option_id=o["option_id"], text=o["text"])
        for o in (q.get("options") or [])
    ]
    return QuizQuestionOut(
        question_id=q["question_id"],
        question_text=q["question_text"],
        question_type=q["question_type"],
        difficulty=q["difficulty"],
        options=options or None,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _current_part_from_status(status: SessionStatus) -> Optional[str]:
    if status in (SessionStatus.STARTED, SessionStatus.PART_A_IN_PROGRESS):
        return "A"
    if status in (SessionStatus.PART_A_COMPLETED, SessionStatus.PART_B_IN_PROGRESS):
        return "B"
    return None


# ---------------------------------------------------------------------------
# Section C -- Service class
# ---------------------------------------------------------------------------

class QuizSessionService:

    SESSION_TTL_DEFAULT = 7200  # 2-hour fallback when test has no duration

    @staticmethod
    async def create_session(db: AsyncSession, data: QuizSessionCreate) -> QuizSession:
        """Create a new quiz session row. TTL derived from test row, not client."""
        test = await TestRepository.get_by_id(db, data.test_id)
        if not test:
            raise HTTPException(status_code=404, detail="Test not found")
        now = datetime.utcnow()
        ttl = test.duration_seconds or QuizSessionService.SESSION_TTL_DEFAULT
        expires = now + timedelta(seconds=ttl)

        # Default part_a config: 3 easy + 4 medium + 4 hard = 11 questions
        pa_cfg = data.part_a_config or PartAConfig()
        pa_cfg_dict = {"easy": pa_cfg.easy, "medium": pa_cfg.medium, "hard": pa_cfg.hard}
        total = data.total_questions or (pa_cfg.easy + pa_cfg.medium + pa_cfg.hard)

        session = QuizSession(
            id=str(uuid.uuid4()),
            test_id=data.test_id,
            submission_id=data.submission_id,
            user_id=data.user_id,
            server_now=now,
            expires_at=expires,
            status=SessionStatus.STARTED,
            total_questions=total,
            part_a={"config": pa_cfg_dict, "questions": []},
            part_b=None,
        )
        return await QuizSessionRepository.create(db, session)

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str) -> QuizSession:
        """Fetch session by ID or raise 404."""
        session = await QuizSessionRepository.get_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @staticmethod
    async def get_session_by_submission(db: AsyncSession, submission_id: int) -> QuizSession:
        """Fetch session by submission_id or raise 404."""
        session = await QuizSessionRepository.get_by_submission_id(db, submission_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for this submission")
        return session

    @staticmethod
    async def get_session_status(db: AsyncSession, session_id: str) -> SessionStatusOut:
        """Return minimal status object."""
        session = await QuizSessionService.get_session(db, session_id)
        return SessionStatusOut(
            session_id=session.id,
            status=session.status,
            current_part=_current_part_from_status(session.status),
        )

    @staticmethod
    async def get_part_a_questions(
        db: AsyncSession,
        session_id: str,
        question_service_url: str,
    ) -> PartAQuestionsOut:
        """
        Fetch Part A questions, update status to PART_A_IN_PROGRESS, store in session.
        If questions already loaded (re-fetch during same part), return cached list.
        """
        session = await QuizSessionRepository.get_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Guard: Part A only accessible in STARTED or PART_A_IN_PROGRESS
        if session.status not in (SessionStatus.STARTED, SessionStatus.PART_A_IN_PROGRESS):
            raise HTTPException(
                status_code=409,
                detail="Cannot fetch Part A questions in status {}".format(session.status),
            )

        part_a_data = session.part_a or {}
        stored_questions = part_a_data.get("questions") or []

        if not stored_questions:
            # First fetch -- load from question service
            config_dict = part_a_data.get("config") or {"easy": 3, "medium": 4, "hard": 4}
            raw_questions = await fetch_questions_for_part(
                question_service_url=question_service_url,
                test_id=session.test_id,
                config=config_dict,
                exclude_ids=[],
            )
            stored_questions = [_normalize_question(q) for q in raw_questions]

            session.part_a = {"config": config_dict, "questions": stored_questions}
            session.status = SessionStatus.PART_A_IN_PROGRESS
            await QuizSessionRepository.save(db, session)
        elif session.status == SessionStatus.STARTED:
            session.status = SessionStatus.PART_A_IN_PROGRESS
            await QuizSessionRepository.save(db, session)

        safe_questions = [_safe_question_out(q) for q in stored_questions]
        return PartAQuestionsOut(
            session_id=session.id,
            questions=safe_questions,
            total_questions=len(safe_questions),
        )

    @staticmethod
    async def submit_part_a(
        db: AsyncSession,
        session_id: str,
        body: PartASubmitIn,
        idempotency_key: Optional[str],
        question_service_url: str,
    ) -> QuizSubmitOut:
        """
        SELECT FOR UPDATE -> check idempotency -> validate status PART_A_IN_PROGRESS
        -> score -> store results -> update status PART_A_COMPLETED -> commit
        """
        session = await QuizSessionRepository.get_by_id_for_update(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # --- Expiry check ---
        if datetime.utcnow() > session.expires_at:
            session.status = SessionStatus.EXPIRED
            await QuizSessionRepository.save(db, session)
            raise HTTPException(status_code=410, detail="Session has expired")

        # --- Idempotency check ---
        if idempotency_key:
            incoming_hash = _sha256(idempotency_key)
            if session.part_a_idempotency_hash is not None:
                if session.part_a_idempotency_hash == incoming_hash:
                    # Replay -- return cached response
                    cached = session.part_a_response_cache or {}
                    return QuizSubmitOut(**cached)
                else:
                    # Key mismatch but part already processed
                    if session.status not in (
                        SessionStatus.STARTED,
                        SessionStatus.PART_A_IN_PROGRESS,
                    ):
                        raise HTTPException(
                            status_code=422,
                            detail="Part A already submitted with a different idempotency key",
                        )

        # --- Status guard ---
        if session.status != SessionStatus.PART_A_IN_PROGRESS:
            if session.status == SessionStatus.STARTED:
                raise HTTPException(
                    status_code=409,
                    detail="Fetch Part A questions before submitting",
                )
            raise HTTPException(
                status_code=409,
                detail="Cannot submit Part A in status {}".format(session.status),
            )

        # --- Score ---
        part_a_data = session.part_a or {}
        stored_questions = part_a_data.get("questions") or []
        if not stored_questions:
            raise HTTPException(status_code=409, detail="Part A questions not loaded")

        answers_dicts = [a.model_dump() for a in body.answers]
        correct_count, pct = score_part(stored_questions, answers_dicts)

        # --- Persist ---
        session.part_a_score = pct
        session.status = SessionStatus.PART_A_COMPLETED

        result_payload = QuizSubmitOut(
            score=pct,
            total_questions=len(stored_questions),
            correct_answers=correct_count,
            analysis="Part A complete. You answered {}/{} correctly ({}%).".format(
                round(correct_count, 1), len(stored_questions), pct
            ),
        )

        if idempotency_key:
            session.part_a_idempotency_hash = _sha256(idempotency_key)
            session.part_a_response_cache = result_payload.model_dump()

        await QuizSessionRepository.save(db, session)
        return result_payload

    @staticmethod
    async def get_part_b_questions(
        db: AsyncSession,
        session_id: str,
        question_service_url: str,
    ) -> PartBQuestionsOut:
        """
        Adaptive: Part A score < 50 -> easier mix, >= 50 -> harder mix.
        Exclude Part A question IDs to avoid repeats.
        """
        session = await QuizSessionRepository.get_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status not in (
            SessionStatus.PART_A_COMPLETED,
            SessionStatus.PART_B_IN_PROGRESS,
        ):
            raise HTTPException(
                status_code=409,
                detail="Cannot fetch Part B questions in status {}".format(session.status),
            )

        part_b_data = session.part_b or {}
        stored_questions = part_b_data.get("questions") or []

        if not stored_questions:
            # Adaptive config based on Part A score
            part_a_score = session.part_a_score or 0.0
            if part_a_score < 50:
                pb_config = {"easy": 5, "medium": 4, "hard": 2}
            else:
                pb_config = {"easy": 2, "medium": 4, "hard": 5}

            # Collect Part A question IDs to exclude
            part_a_data = session.part_a or {}
            part_a_questions = part_a_data.get("questions") or []
            exclude_ids = [q["question_id"] for q in part_a_questions]

            raw_questions = await fetch_questions_for_part(
                question_service_url=question_service_url,
                test_id=session.test_id,
                config=pb_config,
                exclude_ids=exclude_ids,
            )
            stored_questions = [_normalize_question(q) for q in raw_questions]

            session.part_b = {"config": pb_config, "questions": stored_questions}
            session.status = SessionStatus.PART_B_IN_PROGRESS
            await QuizSessionRepository.save(db, session)
        elif session.status == SessionStatus.PART_A_COMPLETED:
            session.status = SessionStatus.PART_B_IN_PROGRESS
            await QuizSessionRepository.save(db, session)

        safe_questions = [_safe_question_out(q) for q in stored_questions]
        part_a_score = session.part_a_score or 0.0
        adaptive_msg = (
            "Part B is calibrated to your performance. Keep going!"
            if part_a_score < 50
            else "Great work on Part A! Part B will challenge you further."
        )

        return PartBQuestionsOut(
            session_id=session.id,
            questions=safe_questions,
            total_questions=len(safe_questions),
            ai_message=adaptive_msg,
        )

    @staticmethod
    async def submit_part_b(
        db: AsyncSession,
        session_id: str,
        body: PartBSubmitIn,
        idempotency_key: Optional[str],
        question_service_url: str,
    ) -> QuizSubmitOut:
        """
        SELECT FOR UPDATE -> idempotency -> validate PART_B_IN_PROGRESS
        -> score -> total = avg(A%, B%) -> update COMPLETED -> commit
        """
        session = await QuizSessionRepository.get_by_id_for_update(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # --- Expiry check ---
        if datetime.utcnow() > session.expires_at:
            session.status = SessionStatus.EXPIRED
            await QuizSessionRepository.save(db, session)
            raise HTTPException(status_code=410, detail="Session has expired")

        # --- Idempotency check ---
        if idempotency_key:
            incoming_hash = _sha256(idempotency_key)
            if session.part_b_idempotency_hash is not None:
                if session.part_b_idempotency_hash == incoming_hash:
                    cached = session.part_b_response_cache or {}
                    return QuizSubmitOut(**cached)
                else:
                    if session.status not in (
                        SessionStatus.PART_A_COMPLETED,
                        SessionStatus.PART_B_IN_PROGRESS,
                    ):
                        raise HTTPException(
                            status_code=422,
                            detail="Part B already submitted with a different idempotency key",
                        )

        # --- Status guard ---
        if session.status != SessionStatus.PART_B_IN_PROGRESS:
            if session.status == SessionStatus.PART_A_COMPLETED:
                raise HTTPException(
                    status_code=409,
                    detail="Fetch Part B questions before submitting",
                )
            raise HTTPException(
                status_code=409,
                detail="Cannot submit Part B in status {}".format(session.status),
            )

        # --- Score Part B ---
        part_b_data = session.part_b or {}
        stored_questions = part_b_data.get("questions") or []
        if not stored_questions:
            raise HTTPException(status_code=409, detail="Part B questions not loaded")

        answers_dicts = [a.model_dump() for a in body.answers]
        correct_count_b, pct_b = score_part(stored_questions, answers_dicts)

        # --- Final score: average of Part A % and Part B % ---
        pct_a = session.part_a_score or 0.0
        total_pct = round((pct_a + pct_b) / 2, 2)

        # --- Persist ---
        session.part_b_score = pct_b
        session.total_score = total_pct
        session.percentage_score = total_pct
        session.status = SessionStatus.COMPLETED

        result_payload = QuizSubmitOut(
            score=total_pct,
            total_questions=len(stored_questions),
            correct_answers=correct_count_b,
            analysis="Quiz complete! Part A: {}%, Part B: {}%, Overall: {}%.".format(
                pct_a, round(pct_b, 2), total_pct
            ),
        )

        if idempotency_key:
            session.part_b_idempotency_hash = _sha256(idempotency_key)
            session.part_b_response_cache = result_payload.model_dump()

        await QuizSessionRepository.save(db, session)

        # Update test_submission to COMPLETED with final score
        if session.submission_id:
            from sqlalchemy import select
            sub_result = await db.execute(
                select(TestSubmission).where(TestSubmission.id == session.submission_id)
            )
            submission = sub_result.scalar_one_or_none()
            if submission:
                submission.status = SubmissionStatus.COMPLETED
                submission.final_score = round(total_pct)
                submission.submitted_at = datetime.utcnow()
                await db.commit()

        return result_payload

    @staticmethod
    async def save_draft(db: AsyncSession, session_id: str, body: DraftSaveIn) -> QuizSession:
        """Last-write-wins draft snapshot. 409 if session not in active state."""
        session = await QuizSessionRepository.get_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        active = {SessionStatus.PART_A_IN_PROGRESS, SessionStatus.PART_B_IN_PROGRESS}
        if session.status not in active:
            raise HTTPException(status_code=409, detail="Session is not active — draft rejected")
        session.draft_answers = body.answers
        return await QuizSessionRepository.save(db, session)
