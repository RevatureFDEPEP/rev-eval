"""Reporting endpoints: candidate results (W4-F1) and trainer-only
aggregates (W4-F3).

Read-only: every query runs against test-management-service's Postgres via
the dedicated TMS engine (get_tms_db). The API gateway verifies the JWT
platform-wide; the trainer endpoints additionally re-verify it themselves
via require_trainer (defense-in-depth — see src/v1/dependencies/auth.py).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_tms_db
from src.schemas.report_schema import (
    AggregateQuery,
    AggregateReport,
    AttemptsPage,
    AttemptsQuery,
    UserSummary,
)
from src.services.report_service import ReportService
from src.v1.dependencies.auth import require_trainer

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/aggregate",
    response_model=AggregateReport,
    dependencies=[Depends(require_trainer)],
)
async def get_aggregate_report(
    query: Annotated[AggregateQuery, Query()],
    db: AsyncSession = Depends(get_tms_db),
):
    """Trainer-only per-test aggregates: attempts, distinct candidates, avg
    score, pass rate vs. the configured threshold, median time-to-complete.
    Optional test/date filters; `min_attempts` drops thin groups (HAVING)."""
    return await ReportService.aggregate_by_test(db, query)


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
