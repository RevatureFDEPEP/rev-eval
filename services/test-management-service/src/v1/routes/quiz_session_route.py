import hashlib
import logging
import random
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.config.settings import settings
from src.db.session import get_db
from src.models.quiz_session import QuizSession, SessionStatus
from src.schemas.quiz_session_schema import (
    PartAQuestionsResponse,
    PartASubmit,
    PartBQuestionsResponse,
    PartBSubmit,
    QuizSessionCreate,
    QuizSessionCreateResponse,
    QuizSessionOut,
    QuizSubmitResponse,
    SessionStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-sessions", tags=["quiz-sessions"])

SESSION_TTL_HOURS = 2


def _sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _fetch_questions(
    skills: Optional[List[str]],
    difficulty: str,
    count: int,
    request_id: str,
) -> List[Dict[str, Any]]:
    """Call question-management-service to get questions by difficulty."""
    question_service_url = settings.QUESTION_SERVICE_URL
    if not question_service_url:
        logger.warning("QUESTION_SERVICE_URL not set — returning empty question list")
        return []
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"X-Request-Id": request_id},
        ) as client:
            params: Dict[str, Any] = {"difficulty": difficulty, "limit": count * 3}
            resp = await client.get(
                f"{question_service_url}/v1/api/questions/by-difficulty/{difficulty}",
                params=params,
            )
            if resp.status_code != 200:
                logger.warning(f"Question service returned {resp.status_code} for difficulty={difficulty}")
                return []
            questions = resp.json()
            if isinstance(questions, dict) and "questions" in questions:
                questions = questions["questions"]
            random.shuffle(questions)
            return questions[:count]
    except Exception as exc:
        logger.error(f"Error fetching questions: {exc}")
        return []


def _score_answers(
    questions: List[Dict[str, Any]],
    answers: List[Dict[str, Any]],
) -> tuple[int, int]:
    """Return (correct_count, total_count). Exact match only (MCQ/multi/true_false)."""
    answer_map: Dict[str, List[int]] = {
        a["question_id"]: a.get("selected_answers", []) for a in answers
    }
    correct = 0
    total = len(questions)
    for q in questions:
        qid = str(q.get("id") or q.get("_id") or q.get("question_id", ""))
        user_ans = set(answer_map.get(qid, []))
        correct_ans = set(q.get("correct_answers") or [])
        if user_ans and user_ans == correct_ans:
            correct += 1
    return correct, total


# ---------------------------------------------------------------------------
# POST /test-sessions/
# ---------------------------------------------------------------------------
@router.post("/", response_model=QuizSessionCreateResponse, status_code=201)
async def create_session(
    payload: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> QuizSessionCreateResponse:
    """
    Create a quiz session.
    - Generates opaque token via secrets.token_urlsafe(32)
    - Stores SHA-256 hash only — raw token returned once and never persisted
    - expires_at and server_now computed server-side
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _sha256(raw_token)
    server_now = datetime.utcnow()
    expires_at = server_now + timedelta(hours=SESSION_TTL_HOURS)

    part_a_cfg = payload.part_a_config.model_dump() if payload.part_a_config else {"easy": 3, "medium": 4, "hard": 4}
    total_a = sum(part_a_cfg.values())
    total_b = (payload.total_questions or 20) - total_a
    if total_b < 0:
        total_b = total_a  # fallback symmetry
    per_b = max(1, total_b // 3)
    part_b_cfg = {"easy": per_b, "medium": per_b, "hard": total_b - 2 * per_b}

    session = QuizSession(
        id=str(uuid.uuid4()),
        token_hash=token_hash,
        test_id=payload.test_id,
        submission_id=payload.submission_id,
        user_id=payload.user_id,
        status=SessionStatus.STARTED,
        server_now=server_now,
        started_at=server_now,
        expires_at=expires_at,
        total_questions=payload.total_questions or 20,
        part_a_config=part_a_cfg,
        part_b_config=part_b_cfg,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    out = QuizSessionOut.from_orm(session)
    return QuizSessionCreateResponse(**out.model_dump(), token=raw_token)


# ---------------------------------------------------------------------------
# GET /test-sessions/by-submission/{submission_id}
# Must be declared before /{session_id} to avoid route shadowing
# ---------------------------------------------------------------------------
@router.get("/by-submission/{submission_id}", response_model=QuizSessionOut)
async def get_session_by_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
) -> QuizSessionOut:
    result = await db.execute(
        select(QuizSession).where(QuizSession.submission_id == submission_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found for submission")
    return QuizSessionOut.from_orm(session)


# ---------------------------------------------------------------------------
# GET /test-sessions/{session_id}
# ---------------------------------------------------------------------------
@router.get("/{session_id}", response_model=QuizSessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> QuizSessionOut:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return QuizSessionOut.from_orm(session)


# ---------------------------------------------------------------------------
# GET /test-sessions/{session_id}/status
# ---------------------------------------------------------------------------
@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionStatusResponse:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    out = QuizSessionOut.from_orm(session)
    return SessionStatusResponse(
        session_id=session.id,
        status=session.status.value,
        current_part=out.current_part,
    )


# ---------------------------------------------------------------------------
# GET /test-sessions/{session_id}/part-a/questions
# ---------------------------------------------------------------------------
@router.get("/{session_id}/part-a/questions", response_model=PartAQuestionsResponse)
async def get_part_a_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> PartAQuestionsResponse:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in (SessionStatus.STARTED, SessionStatus.PART_A_IN_PROGRESS):
        raise HTTPException(status_code=409, detail=f"Cannot get Part A questions in status {session.status}")

    # Return cached questions if already fetched
    if session.part_a and session.part_a.get("questions"):
        questions = session.part_a["questions"]
    else:
        request_id = str(uuid.uuid4())
        cfg = session.part_a_config or {"easy": 3, "medium": 4, "hard": 4}
        questions: List[Dict[str, Any]] = []
        for difficulty, count in cfg.items():
            questions += await _fetch_questions(None, difficulty, count, request_id)
        random.shuffle(questions)

        part_a = {"questions": questions, "answers": [], "score": None, "total_questions": len(questions)}
        session.part_a = part_a
        session.status = SessionStatus.PART_A_IN_PROGRESS
        await db.commit()
        await db.refresh(session)

    # Strip correct_answers before sending to client
    safe_questions = [
        {k: v for k, v in q.items() if k not in ("correct_answers",)}
        for q in questions
    ]
    return PartAQuestionsResponse(
        session_id=session.id,
        questions=safe_questions,
        total_questions=len(safe_questions),
    )


# ---------------------------------------------------------------------------
# POST /test-sessions/{session_id}/part-a/submit
# ---------------------------------------------------------------------------
@router.post("/{session_id}/part-a/submit", response_model=QuizSubmitResponse)
async def submit_part_a(
    session_id: str,
    payload: PartASubmit,
    db: AsyncSession = Depends(get_db),
) -> QuizSubmitResponse:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.PART_A_IN_PROGRESS:
        raise HTTPException(status_code=409, detail=f"Part A not in progress (status: {session.status})")

    questions = (session.part_a or {}).get("questions", [])
    answers_raw = [a.model_dump() for a in payload.answers]
    correct, total = _score_answers(questions, answers_raw)
    score = round((correct / total * 100) if total else 0, 2)

    part_a = session.part_a or {}
    part_a["answers"] = answers_raw
    part_a["score"] = score
    part_a["total_questions"] = total
    part_a["completed_at"] = datetime.utcnow().isoformat()
    session.part_a = part_a
    flag_modified(session, "part_a")
    session.status = SessionStatus.PART_A_COMPLETED
    await db.commit()

    return QuizSubmitResponse(
        score=score,
        total_questions=total,
        correct_answers=correct,
        analysis=f"Part A complete. Score: {score:.1f}% ({correct}/{total} correct).",
    )


# ---------------------------------------------------------------------------
# GET /test-sessions/{session_id}/part-b/questions
# Adaptive: if Part A score < 50%, increase easy questions; else increase hard
# ---------------------------------------------------------------------------
@router.get("/{session_id}/part-b/questions", response_model=PartBQuestionsResponse)
async def get_part_b_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> PartBQuestionsResponse:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in (SessionStatus.PART_A_COMPLETED, SessionStatus.PART_B_IN_PROGRESS):
        raise HTTPException(status_code=409, detail=f"Cannot get Part B in status {session.status}")

    if session.part_b and session.part_b.get("questions"):
        questions = session.part_b["questions"]
        ai_message = session.part_b.get("ai_message")
    else:
        part_a_score = (session.part_a or {}).get("score") or 0
        cfg = dict(session.part_b_config or {"easy": 3, "medium": 4, "hard": 4})

        # Adaptive difficulty shift
        if part_a_score < 50:
            cfg["easy"] = min(cfg.get("easy", 0) + 1, 5)
            cfg["hard"] = max(cfg.get("hard", 0) - 1, 0)
            ai_message = "Focusing on foundational questions based on Part A performance."
        else:
            cfg["hard"] = min(cfg.get("hard", 0) + 1, 6)
            cfg["easy"] = max(cfg.get("easy", 0) - 1, 0)
            ai_message = "Advancing to harder questions based on strong Part A performance."

        request_id = str(uuid.uuid4())
        questions: List[Dict[str, Any]] = []
        for difficulty, count in cfg.items():
            if count > 0:
                questions += await _fetch_questions(None, difficulty, count, request_id)
        random.shuffle(questions)

        part_b = {
            "questions": questions,
            "answers": [],
            "score": None,
            "total_questions": len(questions),
            "ai_message": ai_message,
        }
        session.part_b = part_b
        session.status = SessionStatus.PART_B_IN_PROGRESS
        await db.commit()
        await db.refresh(session)

    safe_questions = [
        {k: v for k, v in q.items() if k not in ("correct_answers",)}
        for q in questions
    ]
    return PartBQuestionsResponse(
        session_id=session.id,
        questions=safe_questions,
        total_questions=len(safe_questions),
        ai_message=session.part_b.get("ai_message") if session.part_b else None,
    )


# ---------------------------------------------------------------------------
# POST /test-sessions/{session_id}/part-b/submit
# ---------------------------------------------------------------------------
@router.post("/{session_id}/part-b/submit", response_model=QuizSubmitResponse)
async def submit_part_b(
    session_id: str,
    payload: PartBSubmit,
    db: AsyncSession = Depends(get_db),
) -> QuizSubmitResponse:
    session = await db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.PART_B_IN_PROGRESS:
        raise HTTPException(status_code=409, detail=f"Part B not in progress (status: {session.status})")

    questions = (session.part_b or {}).get("questions", [])
    answers_raw = [a.model_dump() for a in payload.answers]
    correct, total = _score_answers(questions, answers_raw)
    part_b_score = round((correct / total * 100) if total else 0, 2)

    part_a_score = (session.part_a or {}).get("score") or 0
    total_score = round((part_a_score + part_b_score) / 2, 2)
    percentage_score = total_score

    part_b = session.part_b or {}
    part_b["answers"] = answers_raw
    part_b["score"] = part_b_score
    part_b["completed_at"] = datetime.utcnow().isoformat()
    session.part_b = part_b
    flag_modified(session, "part_b")
    session.total_score = total_score
    session.percentage_score = percentage_score
    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()
    await db.commit()

    return QuizSubmitResponse(
        score=total_score,
        total_questions=total,
        correct_answers=correct,
        analysis=f"Quiz complete. Final score: {total_score:.1f}% (Part A: {part_a_score:.1f}%, Part B: {part_b_score:.1f}%).",
    )
