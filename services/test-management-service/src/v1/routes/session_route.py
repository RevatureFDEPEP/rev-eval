# src/v1/routes/session_route.py
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.answer_schema import AnswerCreate, AnswerResponse
from src.schemas.session_schema import (
    DraftSave,
    DraftSaveResult,
    SessionCreate,
    SessionResponse,
)
from src.services.session_service import SessionService
from src.utils.dependencies import get_current_user_from_headers

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    """Start a quiz session. Open to any authenticated role (trainers may
    self-test); the participant is the resolved current user."""
    return await SessionService.create_session(
        db,
        test_id=body.test_id,
        user_id=current_user["id"],
        correlation_id=x_correlation_id,
    )


@router.post(
    "/{session_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_answer(
    session_id: str,
    body: AnswerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    """Score the answer to the session's current question and advance it.

    Pessimistically locks the session row; a repeated ``Idempotency-Key``
    replays the prior response. Returns 409 once the session is submitted or
    expired."""
    return await SessionService.submit_answer(
        db,
        session_id=session_id,
        user_id=current_user["id"],
        body=body,
        idempotency_key=idempotency_key,
        correlation_id=x_correlation_id,
    )


@router.patch(
    "/{session_id}/draft",
    response_model=DraftSaveResult,
    status_code=status.HTTP_200_OK,
)
async def save_draft(
    session_id: str,
    body: DraftSave,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
):
    """Autosave the candidate's in-progress answers (W3-F4).

    Persists a last-write-wins crash-recovery snapshot WITHOUT scoring or
    advancing the session — ``current_index``/``status`` are returned unchanged.
    Terminal/expired sessions reject with 409 (a semantic error the client must
    surface and halt on, never retry)."""
    return await SessionService.save_draft(
        db,
        session_id=session_id,
        user_id=current_user["id"],
        answers=body.answers,
    )
