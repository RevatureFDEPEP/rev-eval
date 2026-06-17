"""Response envelopes and query-param dependency for the reporting endpoints."""

from datetime import date, datetime
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

from src.models.tms_readonly import QuizSessionStatus

# Columns a client may sort the attempt history by (computed `score` is not a
# column, so it is intentionally excluded).
SORTABLE_FIELDS = {"submitted_at", "created_at", "started_at"}


class AttemptItem(BaseModel):
    session_id: str
    test_id: int
    test_name: str | None = None
    status: QuizSessionStatus
    score: float | None = None  # 0..1 fraction; None when the attempt has no answers
    correct_count: int
    total_answered: int
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    time_spent_seconds: int | None = None


class UserSummaryResponse(BaseModel):
    user_id: int
    total_attempts: int
    average_score: float | None = None  # over attempts that have answers
    best_score: float | None = None
    total_time_spent_seconds: int
    most_recent_attempt: AttemptItem | None = None


class PaginatedAttempts(BaseModel):
    items: list[AttemptItem]
    total: int
    page: int
    size: int


class AttemptsQuery:
    """Query-parameter dependency for ``GET /reports/user/{id}/attempts``.

    Grouped into a single injected dependency rather than loose params. ``from``
    and ``to`` are reserved words, so they are exposed under those names via
    aliases and stored as ``date_from`` / ``date_to``.
    """

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
        size: Annotated[
            int, Query(ge=1, le=100, description="page size (max 100)")
        ] = 20,
        test_id: Annotated[int | None, Query(description="filter to one test")] = None,
        date_from: Annotated[
            date | None,
            Query(alias="from", description="inclusive lower bound on attempt date"),
        ] = None,
        date_to: Annotated[
            date | None,
            Query(alias="to", description="inclusive upper bound on attempt date"),
        ] = None,
        status: Annotated[
            QuizSessionStatus | None, Query(description="filter by status")
        ] = None,
        sort: Annotated[
            str,
            Query(
                pattern=r"^[a-z_]+:(asc|desc)$",
                description="field:direction, e.g. submitted_at:desc",
            ),
        ] = "submitted_at:desc",
    ) -> None:
        self.page = page
        self.size = size
        self.test_id = test_id
        self.date_from = date_from
        self.date_to = date_to
        self.status = status
        self.sort = sort
