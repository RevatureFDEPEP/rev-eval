# src/v1/routes/session_route.py
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.session_schema import SessionCreate, SessionResponse
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
