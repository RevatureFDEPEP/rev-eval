"""Candidate results reporting endpoints (W4-F1).

Read-only: every query runs against test-management-service's Postgres via
the dedicated TMS engine (get_tms_db). The API gateway is the auth boundary
(JWT verified there, like every downstream service); per-role enforcement
(require_trainer / self-access) lands in W4-F3.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_tms_db
from src.schemas.report_schema import AttemptsPage, AttemptsQuery, UserSummary
from src.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/user/{user_id}", response_model=UserSummary)
async def get_user_summary(
    user_id: int,
    db: AsyncSession = Depends(get_tms_db),
):
    """Summary envelope: total attempts, avg/best score, total time spent and
    the most recent attempt — one SQL round trip, aggregated server-side.
    A user with no submitted attempts gets a zeroed envelope, not a 404."""
    return await ReportService.user_summary(db, user_id)


@router.get("/user/{user_id}/attempts", response_model=AttemptsPage)
async def get_user_attempts(
    user_id: int,
    query: Annotated[AttemptsQuery, Query()],
    db: AsyncSession = Depends(get_tms_db),
):
    """Paginated attempt history with filtering (test, date range, status) and
    whitelisted `field:direction` sorting, default `submitted_at:desc`."""
    return await ReportService.user_attempts(db, user_id, query)
