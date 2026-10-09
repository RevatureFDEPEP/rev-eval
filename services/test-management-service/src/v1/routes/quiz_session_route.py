# src/v1/routes/quiz_session_route.py
from fastapi import APIRouter, Depends, Header, HTTPException, status
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.config.settings import settings
from src.models.quiz_session import QuizSession
from src.repositories.test_repository import TestRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.services.quiz_session_service import QuizSessionService
from src.utils.authorization import caller_id, forbidden, is_trainer, trainer_manages_test
from src.utils.dependencies import get_current_user
from src.schemas.quiz_session_schema import (
    QuizSessionCreate,
    DraftSaveIn,
    QuizSessionOut,
    PartAQuestionsOut,
    PartBQuestionsOut,
    PartASubmitIn,
    PartBSubmitIn,
    QuizSubmitOut,
    SessionStatusOut,
)

router = APIRouter(prefix="/test-sessions", tags=["Quiz Sessions"])

# A quiz session belongs to one participant. Only that participant can start,
# answer, autosave or submit it; the trainer who manages the test can also
# read it (the review screens show the graded quiz). Ownership is checked
# against the stored session before any read or write.


async def _readable_session(db: AsyncSession, session: QuizSession, user: Dict) -> QuizSession:
    if session.user_id == caller_id(user):
        return session
    if is_trainer(user):
        test = await TestRepository.get_by_id(db, session.test_id)
        if test is not None and trainer_manages_test(user, test):
            return session
    raise forbidden("You can only access your own quiz sessions")


async def _own_session(db: AsyncSession, session_id: str, user: Dict) -> QuizSession:
    session = await QuizSessionService.get_session(db, session_id)
    if session.user_id != caller_id(user):
        raise forbidden("You can only take your own quiz sessions")
    return session


@router.post("/", response_model=QuizSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Start a quiz session for one of the caller's own submissions. TTL derived
    from test.duration_seconds server-side.
    """
    own_id = caller_id(current_user)
    if data.user_id != own_id:
        raise forbidden("You can only start a quiz session for yourself")
    submission = await TestSubmissionRepository.get_by_id(db, data.submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.user_id != own_id or submission.test_id != data.test_id:
        raise forbidden("This submission is not assigned to you for this test")
    session = await QuizSessionService.create_session(db, data)
    return _session_to_out(session)


# IMPORTANT: /by-submission/{submission_id} MUST be registered before /{session_id}
# to avoid FastAPI matching "by-submission" as a session_id path parameter.
@router.get("/by-submission/{submission_id}", response_model=QuizSessionOut)
async def get_session_by_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Get the quiz session associated with a specific submission."""
    session = await QuizSessionService.get_session_by_submission(db, submission_id)
    return _session_to_out(await _readable_session(db, session, current_user))


@router.get("/{session_id}", response_model=QuizSessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Get full quiz session details."""
    session = await QuizSessionService.get_session(db, session_id)
    return _session_to_out(await _readable_session(db, session, current_user))


@router.get("/{session_id}/status", response_model=SessionStatusOut)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Get minimal session status without full session data."""
    await _readable_session(db, await QuizSessionService.get_session(db, session_id), current_user)
    return await QuizSessionService.get_session_status(db, session_id)


@router.get("/{session_id}/part-a/questions", response_model=PartAQuestionsOut)
async def get_part_a_questions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Fetch Part A questions (3 easy, 4 medium, 4 hard by default)."""
    await _own_session(db, session_id, current_user)
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
    current_user: Dict = Depends(get_current_user),
):
    """
    Submit Part A answers. Uses SELECT FOR UPDATE to prevent concurrent double-submit.
    Idempotency-Key header: same key replays cached response; absent means no protection.
    """
    await _own_session(db, session_id, current_user)
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
    current_user: Dict = Depends(get_current_user),
):
    """Fetch Part B questions. Difficulty adapted to Part A score (<50% easier, >=50% harder)."""
    await _own_session(db, session_id, current_user)
    return await QuizSessionService.get_part_b_questions(
        db,
        session_id,
        settings.QUESTION_SERVICE_URL,
    )


@router.patch("/{session_id}/draft", response_model=QuizSessionOut)
async def save_draft(
    session_id: str,
    body: DraftSaveIn,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Save draft answers last-write-wins. 409 if session not in active state."""
    await _own_session(db, session_id, current_user)
    session = await QuizSessionService.save_draft(db, session_id, body)
    return _session_to_out(session)


@router.post("/{session_id}/part-b/submit", response_model=QuizSubmitOut)
async def submit_part_b(
    session_id: str,
    body: PartBSubmitIn,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Submit Part B answers and finalize the quiz.
    Final score = average(Part A %, Part B %). Uses SELECT FOR UPDATE.
    """
    await _own_session(db, session_id, current_user)
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
        expires_at=session.expires_at,
        completed_at=session.completed_at,
        total_questions=session.total_questions,
        part_a_config=part_a_data.get("config") or session.part_a_config,
        part_b_config=part_b_data.get("config") or session.part_b_config,
        part_a=session.part_a,
        part_b=session.part_b,
        draft_answers=session.draft_answers,
        total_score=session.total_score,
        percentage_score=session.percentage_score,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
