from datetime import date, datetime
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from src.models.session_mirror import AttemptStatus

# Fields a client may sort the attempts list by (maps name -> model column name).
SORTABLE_FIELDS = {
    "created_at",
    "submitted_at",
    "started_at",
    "score",
    "time_spent_seconds",
}


class AttemptOut(BaseModel):
    """A single quiz attempt as returned by the reporting endpoints."""

    session_id: str
    user_id: int
    test_id: Optional[str] = None
    status: AttemptStatus
    score: float
    time_spent_seconds: int
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserReportSummary(BaseModel):
    """Summary envelope for GET /reports/user/{user_id}."""

    user_id: int
    total_attempts: int
    average_score: float
    best_score: float
    total_time_spent: int
    most_recent_attempt: Optional[AttemptOut] = None


class PaginatedAttempts(BaseModel):
    """Paginated envelope for GET /reports/user/{user_id}/attempts."""

    items: List[AttemptOut]
    total: int
    page: int
    size: int
    pages: int


@dataclass
class AttemptFilters:
    """Validated query parameters for the attempts endpoint.

    A Pydantic dataclass — the injected dependency object. Bound from the
    request by :func:`attempt_filters` so FastAPI fully processes the per-field
    ``Query`` metadata (aliases, bounds, pattern → proper 422 responses).
    """

    page: int = 1
    size: int = 20
    test_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[AttemptStatus] = None
    sort: str = "created_at:desc"


def attempt_filters(
    page: int = Query(1, ge=1, description="1-based page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    test_id: Optional[str] = Query(None, description="Filter by test identifier"),
    date_from: Optional[date] = Query(
        None, alias="from", description="Only attempts created on/after this date"
    ),
    date_to: Optional[date] = Query(
        None, alias="to", description="Only attempts created on/before this date"
    ),
    status: Optional[AttemptStatus] = Query(
        None, description="Filter by attempt status"
    ),
    sort: str = Query(
        "created_at:desc",
        pattern=r"^[a-zA-Z_]+:(asc|desc)$",
        description="Sort as field:direction, e.g. score:desc",
    ),
) -> AttemptFilters:
    """Bind and validate query parameters into an ``AttemptFilters`` dataclass."""
    return AttemptFilters(
        page=page,
        size=size,
        test_id=test_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        sort=sort,
    )
