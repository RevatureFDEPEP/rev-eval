# src/v1/routes/reports_route.py
"""Candidate reporting endpoints (W4-F1).

Read-heavy GETs over test-management-service's tables via the read-only TMS
engine (get_tms_db):
  GET /reports/user/{user_id}           -> summary envelope
  GET /reports/user/{user_id}/attempts  -> paginated attempt history

Service-level authorization is intentionally absent here: the API gateway's JWT
check is the platform-wide boundary, as for every downstream service. The
``require_trainer`` gate and self-access enforcement land in W4-F3.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_tms_db
from src.schemas.reports_schema import AttemptsPage, AttemptsQuery, UserSummary
from src.services import reports_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/user/{user_id}", response_model=UserSummary)
async def get_user_summary(
    user_id: int,
    db: AsyncSession = Depends(get_tms_db),
):
    """Per-candidate results summary over SUBMITTED attempts: total attempts,
    average/best score (0..100), total time spent, and the most recent attempt."""
    return await reports_service.get_user_summary(db, user_id)


@router.get("/user/{user_id}/attempts", response_model=AttemptsPage)
async def get_user_attempts(
    user_id: int,
    query: Annotated[AttemptsQuery, Query()],
    db: AsyncSession = Depends(get_tms_db),
):
    """Paginated attempt history with test/date/status filters and field:direction
    sort (default submitted_at:desc). Score is null until an attempt is SUBMITTED."""
    return await reports_service.get_user_attempts(db, user_id, query)
