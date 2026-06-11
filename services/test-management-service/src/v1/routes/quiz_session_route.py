import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.quiz_session_schema import QuizSessionCreate, QuizSessionStartResponse
from src.services.quiz_session_service import QuizSessionService
from src.utils.dependencies import get_current_participant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["quiz-sessions"])


@router.post(
    "",
    response_model=QuizSessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quiz session",
    description=(
        "Mint a server-authoritative quiz session. "
        "Returns session timing, an opaque session token, and the first question "
        "(without correct answers)."
    ),
)
async def create_quiz_session(
    payload: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> QuizSessionStartResponse:
    correlation_id = x_correlation_id or x_request_id
    return await QuizSessionService.create_session(db, payload, current_user, correlation_id)
