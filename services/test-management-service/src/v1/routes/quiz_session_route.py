from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.quiz_session_schema import (
    DraftSaveRequest,
    DraftSaveResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionStateResponse,
)
from src.schemas.session_answer_schema import AnswerResult, AnswerSubmitRequest
from src.services.quiz_session_scoring_service import QuizSessionScoringService
from src.services.quiz_session_service import QuizSessionError, QuizSessionService
from src.utils.dependencies import get_current_participant_id

router = APIRouter(prefix="/sessions", tags=["Quiz Sessions"])


@router.post(
    "", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_session(
    request: SessionCreateRequest,
    user_id: int = Depends(get_current_participant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a quiz session for the authenticated participant.

    Mints a session with server-authoritative timing and a frozen, ordered set
    of questions, and returns the first question (answers stripped).
    Re-posting for the same test returns the existing active session.
    """
    try:
        return await QuizSessionService.create_session(db, request.test_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except QuizSessionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.post("/{session_id}/answer", response_model=AnswerResult)
async def submit_answer(
    session_id: str,
    request: AnswerSubmitRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    user_id: int = Depends(get_current_participant_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer for the current question, advance the session, and
    return the next question (or completion state when all questions answered).

    A non-empty Idempotency-Key header is required so a retried submit replays
    the original result instead of double-scoring (422 if missing or blank)."""
    try:
        return await QuizSessionScoringService.submit_answer(
            db, session_id, user_id, request, idempotency_key
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except QuizSessionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.patch("/{session_id}/draft", response_model=DraftSaveResponse)
async def save_draft(
    session_id: str,
    request: DraftSaveRequest,
    user_id: int = Depends(get_current_participant_id),
    db: AsyncSession = Depends(get_db),
):
    """Autosave the participant's in-progress selections (advisory snapshot).

    Persists the answer map without scoring, advancing current_index, or
    changing status. Last-write-wins (no Idempotency-Key). A non-active or
    expired session is rejected with 409 so the client halts rather than
    retrying."""
    try:
        return await QuizSessionService.save_draft(
            db, session_id, user_id, request.answers, request.client_version
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except QuizSessionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    user_id: int = Depends(get_current_participant_id),
    db: AsyncSession = Depends(get_db),
):
    """Return current session state (with lazy expiry) for the owning participant."""
    try:
        return await QuizSessionService.get_session(db, session_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except QuizSessionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
