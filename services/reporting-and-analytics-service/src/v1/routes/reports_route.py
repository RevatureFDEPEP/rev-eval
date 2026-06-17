"""Candidate reporting endpoints (W4-F1).

NOTE on authorization: these endpoints are reachable only through the API
gateway, which verifies the JWT before forwarding. Per-role / per-owner access
control (a participant may read only their own results; trainers may read any)
is added in W4-F3 via a ``require_trainer`` / ownership dependency reading the
gateway-injected ``X-User-Role`` / ``X-User-Id`` headers. Until then these are
authenticated-but-not-authorized — tracked as the F3 gate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.reporting_schema import (
    AttemptsQuery,
    PaginatedAttempts,
    UserSummaryResponse,
)
from src.services.reporting_service import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/user/{user_id}", response_model=UserSummaryResponse)
async def get_user_summary(user_id: int, db: AsyncSession = Depends(get_db)):
    """Aggregate results summary for one candidate."""
    return await ReportingService.get_user_summary(db, user_id)


@router.get("/user/{user_id}/attempts", response_model=PaginatedAttempts)
async def get_user_attempts(
    user_id: int,
    q: AttemptsQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable attempt history for one candidate."""
    return await ReportingService.get_user_attempts(db, user_id, q)
