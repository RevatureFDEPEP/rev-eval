import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.session_schema import SessionCreateRequest, SessionResponse
from src.services import session_service
from src.utils.dependencies import get_current_participant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    raw_id = current_user.get("id") or current_user.get("user_id")
    if raw_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID missing from auth context")
    user_id = int(raw_id)
    return await session_service.create_session(
        db=db,
        quiz_id=body.quiz_id,
        user_id=user_id,
        correlation_id=correlation_id,
    )
