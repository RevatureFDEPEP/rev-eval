import uuid

import httpx
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.session_schema import AnswerResponse, AnswerSubmit, SessionCreate, SessionOut
from src.services.session_service import SessionService
from src.utils.dependencies import get_current_user_from_headers, get_http_client

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionOut, status_code=201)
async def create_session(
    session_in: SessionCreate,
    current_user: dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    return await SessionService.create_session(
        db, session_in, int(current_user["id"]), http_client, x_correlation_id
    )


@router.post("/{session_id}/answers", response_model=AnswerResponse, status_code=200)
async def submit_answer(
    session_id: uuid.UUID,
    answer_in: AnswerSubmit,
    current_user: dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-Id"),
):
    return await SessionService.submit_answer(
        db, session_id, answer_in, int(current_user["id"]),
        http_client, idempotency_key, x_correlation_id,
    )
