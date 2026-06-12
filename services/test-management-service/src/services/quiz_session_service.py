"""Business logic for the secure quiz-taking vertical slice.

Security / correctness invariants enforced here:

* Timing is server-authoritative — ``expires_at`` is computed from the server
  clock at creation and every lock decision compares against ``datetime.utcnow``,
  never a client-supplied time.
* Answer keys never leave the service for participants. The full question
  (with ``correct_answers``) lives only in ``snapshot_json``; participant
  payloads are built through ``QuizQuestionOut``.
* Answer submission and final submission take a row-level lock on the session
  (``with_for_update``) before reading/mutating attempt state.
* Submitted and expired sessions are immutable — draft saves and answer
  submissions are rejected.
* ``Idempotency-Key`` makes answer submission a safe retry: same key + same
  payload replays the stored response; same key + different payload is a 409.
"""
import hashlib
import json
import logging
import os
import random
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.quiz_session import (
    IdempotencyRecord,
    QuizAnswer,
    QuizSession,
    QuizSessionQuestion,
    SessionStatus,
)
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.quiz_session_schema import (
    AnswerResultResponse,
    AnswerSubmit,
    DraftPatch,
    DraftResponse,
    QuizQuestionOut,
    QuizSessionCreate,
    QuizSessionStartResponse,
    QuizSessionStateResponse,
    QuizSubmitResponse,
)

logger = logging.getLogger(__name__)

_QUESTION_SERVICE_URL = os.getenv(
    "QUESTION_SERVICE_URL", "http://question-management-service:8003"
)
_DEFAULT_DURATION = timedelta(hours=1)

# Coarse anti-abuse guard: maximum concurrent in-progress sessions per user.
_MAX_ACTIVE_SESSIONS_PER_USER = 25

# Question fields that must never reach a participant. The full question
# (including these) is persisted in snapshot_json for server-side scoring.
_SENSITIVE_QUESTION_FIELDS = ("correct_answers", "answer_explanation", "sample_answer")

_AUTO_SCORABLE_TYPES = {"mcq", "true_false", "multi"}


def _question_id(question: Dict[str, Any]) -> str:
    return str(question.get("_id") or question.get("id") or "")


def _safe_question(snapshot: QuizSessionQuestion) -> QuizQuestionOut:
    """Build the participant-facing view of a stored question snapshot."""
    q = snapshot.snapshot_json or {}
    return QuizQuestionOut(
        question_id=snapshot.question_id,
        question_index=snapshot.question_index,
        question_type=snapshot.question_type or q.get("type", ""),
        question_text=q.get("question_text", ""),
        options=q.get("options"),
    )


def _safe_question_from_dict(question: Dict[str, Any], index: int) -> QuizQuestionOut:
    return QuizQuestionOut(
        question_id=_question_id(question),
        question_index=index,
        question_type=question.get("type", ""),
        question_text=question.get("question_text", ""),
        options=question.get("options"),
    )


def _fingerprint(payload: AnswerSubmit) -> str:
    """Stable hash of an answer payload for idempotency-key conflict detection."""
    canonical = json.dumps(
        {
            "question_id": payload.question_id,
            "selected_answers": sorted(payload.selected_answers, key=repr),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_expires_at(server_now: datetime, duration) -> datetime:
    """Compute session expiry from test.duration (timedelta) or the default."""
    if duration is not None:
        return server_now + duration
    return server_now + _DEFAULT_DURATION


async def _fetch_questions(
    n: int, correlation_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    # This is a trusted server-to-server call. It identifies as ADMIN so the
    # question service returns the FULL question (answer keys included) for the
    # server-only snapshot. question-management-service must not be reachable by
    # clients except through the gateway (which sets the real caller role) —
    # see docker-compose port hardening.
    headers: Dict[str, str] = {"X-User-Role": "ADMIN"}
    if correlation_id:
        headers["X-Correlation-Id"] = correlation_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{_QUESTION_SERVICE_URL}/v1/api/questions/",
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.error("question-management-service unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="question-management-service is unreachable",
        )

    if response.status_code != 200:
        logger.error(
            "question-management-service returned %d: %s",
            response.status_code,
            response.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"question-management-service returned {response.status_code}",
        )

    pool: List[Dict[str, Any]] = response.json()
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question pool is empty — cannot create quiz session",
        )

    if len(pool) >= n:
        return random.sample(pool, n)
    return pool


def _possible_for(question_type: str) -> float:
    return 1.0 if (question_type or "").lower() in _AUTO_SCORABLE_TYPES else 0.0


class QuizSessionService:

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _require_owner(session: QuizSession, current_user: Dict[str, Any]) -> None:
        if session.user_id != current_user["id"]:
            # 404 (not 403) so we don't confirm the existence of another user's
            # session to an unauthorized caller.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

    @staticmethod
    async def _load_owned(
        db: AsyncSession,
        session_id: str,
        current_user: Dict[str, Any],
        *,
        lock: bool,
    ) -> QuizSession:
        if lock:
            session = await QuizSessionRepository.get_by_session_id_for_update(
                db, session_id
            )
        else:
            session = await QuizSessionRepository.get_by_session_id(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )
        QuizSessionService._require_owner(session, current_user)
        return session

    @staticmethod
    async def _expire_if_due(
        db: AsyncSession, session: QuizSession, now: datetime
    ) -> bool:
        """Flip an in-progress session to EXPIRED if past its deadline.

        Returns True if the session is (now) expired. Server clock is the only
        authority — the client's timer is advisory.
        """
        if session.status == SessionStatus.in_progress and now >= session.expires_at:
            session.status = SessionStatus.expired
            await db.flush()
            return True
        return session.status == SessionStatus.expired

    @staticmethod
    def _guard_mutable(session: QuizSession, expired: bool) -> None:
        if session.status == SessionStatus.submitted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session already submitted",
            )
        if expired or session.status == SessionStatus.expired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has expired",
            )

    # ------------------------------------------------------------------- create
    @staticmethod
    async def create_session(
        db: AsyncSession,
        payload: QuizSessionCreate,
        current_user: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> QuizSessionStartResponse:
        user_id = current_user["id"]

        test = await TestRepository.get_by_id(db, payload.test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {payload.test_id} not found",
            )
        if not test.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Test is not active"
            )

        # IDOR guard: a supplied submission must belong to this user and test.
        if payload.submission_id is not None:
            submission = await TestSubmissionRepository.get_by_id(
                db, payload.submission_id
            )
            if submission is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Submission {payload.submission_id} not found",
                )
            if submission.user_id != user_id or submission.test_id != payload.test_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Submission does not belong to this user and test",
                )

        active_count = await QuizSessionRepository.count_active_for_user(db, user_id)
        if active_count >= _MAX_ACTIVE_SESSIONS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many active quiz sessions; finish or abandon one first",
            )

        n_questions = test.number_of_questions or 20
        questions = await _fetch_questions(n_questions, correlation_id)

        server_now = datetime.utcnow()
        expires_at = compute_expires_at(server_now, test.duration)

        session = QuizSession(
            session_id=uuid.uuid4().hex,
            test_id=payload.test_id,
            submission_id=payload.submission_id,
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            status=SessionStatus.in_progress,
            current_index=0,
            draft_answers={},
            server_started_at=server_now,
            expires_at=expires_at,
            created_at=server_now,
            updated_at=server_now,
        )
        await QuizSessionRepository.create(db, session)

        for idx, q in enumerate(questions):
            await QuizSessionRepository.add_question(
                db,
                QuizSessionQuestion(
                    quiz_session_id=session.id,
                    question_id=_question_id(q),
                    question_index=idx,
                    question_type=q.get("type", ""),
                    snapshot_json=q,
                ),
            )

        await db.commit()
        await db.refresh(session)

        logger.info(
            "quiz session created",
            extra={
                "session_id": session.session_id,
                "test_id": payload.test_id,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "question_count": len(questions),
            },
        )

        return QuizSessionStartResponse(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=server_now,
            expires_at=expires_at,
            status=session.status.value,
            current_index=0,
            total_questions=len(questions),
            question=_safe_question_from_dict(questions[0], 0),
        )

    # ---------------------------------------------------------------------- get
    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: str, current_user: Dict[str, Any]
    ) -> QuizSessionStateResponse:
        session = await QuizSessionService._load_owned(
            db, session_id, current_user, lock=False
        )
        now = datetime.utcnow()
        # Lazily mark an overdue session expired so reads reflect the lock state.
        if session.status == SessionStatus.in_progress and now >= session.expires_at:
            session.status = SessionStatus.expired
            await db.commit()
            await db.refresh(session)

        snapshots = await QuizSessionRepository.get_questions_for_session(
            db, session.id
        )
        return QuizSessionStateResponse(
            session_id=session.session_id,
            status=session.status.value,
            server_now=now,
            expires_at=session.expires_at,
            current_index=session.current_index,
            total_questions=len(snapshots),
            draft_answers=session.draft_answers or {},
            questions=[_safe_question(s) for s in snapshots],
            total_score=session.total_score,
            max_score=session.max_score,
            percentage_score=session.percentage_score,
        )

    # -------------------------------------------------------------------- draft
    @staticmethod
    async def save_draft(
        db: AsyncSession,
        session_id: str,
        patch: DraftPatch,
        current_user: Dict[str, Any],
    ) -> DraftResponse:
        session = await QuizSessionService._load_owned(
            db, session_id, current_user, lock=True
        )
        now = datetime.utcnow()
        expired = await QuizSessionService._expire_if_due(db, session, now)
        if expired or session.status == SessionStatus.expired:
            await db.commit()
        QuizSessionService._guard_mutable(session, expired)

        # Merge so partial autosaves accumulate rather than clobber the buffer.
        if patch.answers is not None:
            merged = dict(session.draft_answers or {})
            merged.update(patch.answers)
            session.draft_answers = merged
        if patch.current_index is not None:
            session.current_index = patch.current_index

        await db.commit()
        await db.refresh(session)

        return DraftResponse(
            session_id=session.session_id,
            status=session.status.value,
            server_now=now,
            expires_at=session.expires_at,
            current_index=session.current_index,
            draft_answers=session.draft_answers or {},
        )

    # ------------------------------------------------------------- submit answer
    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: str,
        payload: AnswerSubmit,
        current_user: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> AnswerResultResponse:
        from src.scoring import score_question

        session = await QuizSessionService._load_owned(
            db, session_id, current_user, lock=True
        )
        now = datetime.utcnow()
        expired = await QuizSessionService._expire_if_due(db, session, now)
        if expired:
            await db.commit()
        QuizSessionService._guard_mutable(session, expired)

        # Idempotency replay / conflict — checked under the row lock.
        fingerprint = _fingerprint(payload)
        if idempotency_key:
            record = await QuizSessionRepository.get_idempotency_record(
                db, session.id, idempotency_key
            )
            if record is not None:
                if record.request_fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key reused with a different payload",
                    )
                return AnswerResultResponse(**record.response_payload)

        snapshots = await QuizSessionRepository.get_questions_for_session(
            db, session.id
        )
        snapshot = next(
            (s for s in snapshots if s.question_id == payload.question_id), None
        )
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question is not part of this session",
            )

        correct_answers = (snapshot.snapshot_json or {}).get("correct_answers")
        result = score_question(
            snapshot.question_type, correct_answers, payload.selected_answers
        )

        # Upsert the latest answer for this question.
        answer = await QuizSessionRepository.get_answer(
            db, session.id, snapshot.question_index
        )
        if answer is None:
            answer = QuizAnswer(
                quiz_session_id=session.id,
                question_id=snapshot.question_id,
                question_index=snapshot.question_index,
            )
            await QuizSessionRepository.add_answer(db, answer)
        answer.submitted_answers = list(payload.selected_answers)
        answer.is_correct = result.is_correct
        answer.earned = result.earned
        answer.possible = result.possible
        answer.algorithm = (
            "partial_credit"
            if (snapshot.question_type or "").lower() == "multi"
            else "exact_match"
        )

        # Advance the cursor to the furthest answered question.
        session.current_index = max(session.current_index, snapshot.question_index)

        await db.flush()
        answered_count = len(
            await QuizSessionRepository.get_answers_for_session(db, session.id)
        )

        response = AnswerResultResponse(
            session_id=session.session_id,
            question_id=snapshot.question_id,
            recorded=True,
            answered_count=answered_count,
            total_questions=len(snapshots),
            server_now=now,
            expires_at=session.expires_at,
        )

        if idempotency_key:
            await QuizSessionRepository.add_idempotency_record(
                db,
                IdempotencyRecord(
                    quiz_session_id=session.id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    response_payload=response.model_dump(mode="json"),
                ),
            )

        await db.commit()
        return response

    # ------------------------------------------------------------------- submit
    @staticmethod
    async def submit_session(
        db: AsyncSession, session_id: str, current_user: Dict[str, Any]
    ) -> QuizSubmitResponse:
        session = await QuizSessionService._load_owned(
            db, session_id, current_user, lock=True
        )

        snapshots = await QuizSessionRepository.get_questions_for_session(
            db, session.id
        )
        answers = await QuizSessionRepository.get_answers_for_session(db, session.id)

        # Idempotent submit: a finalized session replays its stored tally.
        if session.status == SessionStatus.submitted:
            return QuizSessionService._build_submit_response(session, snapshots, answers)

        now = datetime.utcnow()
        max_score = sum(_possible_for(s.question_type) for s in snapshots)
        total_score = sum(a.earned for a in answers)
        percentage = (total_score / max_score * 100.0) if max_score > 0 else 0.0

        session.total_score = total_score
        session.max_score = max_score
        session.percentage_score = percentage
        session.submitted_at = now
        # A session past its deadline finalizes as EXPIRED; otherwise SUBMITTED.
        if now >= session.expires_at:
            session.status = SessionStatus.expired
        else:
            session.status = SessionStatus.submitted

        await db.commit()
        await db.refresh(session)

        logger.info(
            "quiz session finalized",
            extra={
                "session_id": session.session_id,
                "user_id": session.user_id,
                "status": session.status.value,
                "total_score": total_score,
                "max_score": max_score,
            },
        )
        return QuizSessionService._build_submit_response(session, snapshots, answers)

    @staticmethod
    def _build_submit_response(
        session: QuizSession,
        snapshots: List[QuizSessionQuestion],
        answers: List[QuizAnswer],
    ) -> QuizSubmitResponse:
        correct_count = sum(1 for a in answers if a.is_correct)
        return QuizSubmitResponse(
            session_id=session.session_id,
            status=session.status.value,
            submitted_at=session.submitted_at or datetime.utcnow(),
            total_score=session.total_score or 0.0,
            max_score=session.max_score or 0.0,
            percentage_score=session.percentage_score or 0.0,
            correct_count=correct_count,
            answered_count=len(answers),
            total_questions=len(snapshots),
        )
