from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import (
    AttemptFilters,
    AttemptOut,
    PaginatedAttempts,
    UserReportSummary,
    attempt_filters,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/user/{user_id}", response_model=UserReportSummary)
async def get_user_summary(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a summary envelope of a user's quiz attempts.

    Aggregates total attempts, average score, best score, total time spent and
    the most recent attempt in a single SQLAlchemy query (see ADR 0001).
    """
    (
        total_attempts,
        average_score,
        best_score,
        total_time_spent,
        most_recent,
    ) = await ReportRepository.get_user_summary(db, user_id)

    return UserReportSummary(
        user_id=user_id,
        total_attempts=total_attempts,
        average_score=average_score,
        best_score=best_score,
        total_time_spent=total_time_spent,
        most_recent_attempt=(
            AttemptOut.model_validate(most_recent) if most_recent else None
        ),
    )


@router.get("/user/{user_id}/attempts", response_model=PaginatedAttempts)
async def list_user_attempts(
    user_id: int,
    filters: AttemptFilters = Depends(attempt_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated, filtered, sorted list of a user's attempts."""
    try:
        items, total = await ReportRepository.list_attempts(db, user_id, filters)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    pages = ceil(total / filters.size) if total else 0
    return PaginatedAttempts(
        items=[AttemptOut.model_validate(i) for i in items],
        total=total,
        page=filters.page,
        size=filters.size,
        pages=pages,
    )
