from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.quiz_session_schema import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionStateResponse,
)
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
