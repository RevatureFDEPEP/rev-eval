from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.quiz_session_schema import CreateSessionRequest, SessionResponse
from src.services.quiz_session_service import QuizSessionService
from src.utils.dependencies import get_current_user_from_headers

router = APIRouter(prefix="/sessions", tags=["Quiz Sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
):
    user_id: int = int(current_user["id"])
    try:
        return await QuizSessionService.create_session(
            db, body, user_id, correlation_id=x_correlation_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
