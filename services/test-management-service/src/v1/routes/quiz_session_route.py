# src/v1/routes/quiz_session_route.py
from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.config.settings import settings
from src.services.quiz_session_service import QuizSessionService
from src.schemas.quiz_session_schema import (
    QuizSessionCreate,
    QuizSessionOut,
    PartAQuestionsOut,
    PartBQuestionsOut,
    PartASubmitIn,
    PartBSubmitIn,
    QuizSubmitOut,
    SessionStatusOut,
)

router = APIRouter(prefix="/test-sessions", tags=["Quiz Sessions"])


@router.post("/", response_model=QuizSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new quiz session. TTL derived from test.duration_seconds server-side."""
    session = await QuizSessionService.create_session(db, data)
    return _session_to_out(session)


# IMPORTANT: /by-submission/{submission_id} MUST be registered before /{session_id}
# to avoid FastAPI matching "by-submission" as a session_id path parameter.
@router.get("/by-submission/{submission_id}", response_model=QuizSessionOut)
async def get_session_by_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the quiz session associated with a specific submission."""
    session = await QuizSessionService.get_session_by_submission(db, submission_id)
    return _session_to_out(session)


@router.get("/{session_id}", response_model=QuizSessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full quiz session details."""
    session = await QuizSessionService.get_session(db, session_id)
    return _session_to_out(session)


@router.get("/{session_id}/status", response_model=SessionStatusOut)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get minimal session status without full session data."""
    return await QuizSessionService.get_session_status(db, session_id)


@router.get("/{session_id}/part-a/questions", response_model=PartAQuestionsOut)
async def get_part_a_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch Part A questions (3 easy, 4 medium, 4 hard by default)."""
    return await QuizSessionService.get_part_a_questions(
        db,
        session_id,
        settings.QUESTION_SERVICE_URL,
    )


@router.post("/{session_id}/part-a/submit", response_model=QuizSubmitOut)
async def submit_part_a(
    session_id: str,
    body: PartASubmitIn,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit Part A answers. Uses SELECT FOR UPDATE to prevent concurrent double-submit.
    Idempotency-Key header: same key replays cached response; absent means no protection.
    """
    return await QuizSessionService.submit_part_a(
        db,
        session_id,
        body,
        idempotency_key,
        settings.QUESTION_SERVICE_URL,
    )


@router.get("/{session_id}/part-b/questions", response_model=PartBQuestionsOut)
async def get_part_b_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch Part B questions. Difficulty adapted to Part A score (<50% easier, >=50% harder)."""
    return await QuizSessionService.get_part_b_questions(
        db,
        session_id,
        settings.QUESTION_SERVICE_URL,
    )


@router.post("/{session_id}/part-b/submit", response_model=QuizSubmitOut)
async def submit_part_b(
    session_id: str,
    body: PartBSubmitIn,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit Part B answers and finalize the quiz.
    Final score = average(Part A %, Part B %). Uses SELECT FOR UPDATE.
    """
    return await QuizSessionService.submit_part_b(
        db,
        session_id,
        body,
        idempotency_key,
        settings.QUESTION_SERVICE_URL,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _session_to_out(session) -> QuizSessionOut:
    part_a_data = session.part_a or {}
    part_b_data = session.part_b or {}
    return QuizSessionOut(
        id=session.id,
        test_id=session.test_id,
        submission_id=session.submission_id,
        user_id=session.user_id,
        status=session.status,
        started_at=session.server_now,
        completed_at=session.completed_at,
        total_questions=session.total_questions,
        part_a_config=part_a_data.get("config") or session.part_a_config,
        part_b_config=part_b_data.get("config") or session.part_b_config,
        part_a=session.part_a,
        part_b=session.part_b,
        total_score=session.total_score,
        percentage_score=session.percentage_score,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
