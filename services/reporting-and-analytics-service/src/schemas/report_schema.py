"""Pydantic schemas for the candidate results reporting endpoints (W4-F1)."""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.tms_readonly import SessionStatus

SORT_FIELDS = {"submitted_at", "created_at", "score"}
SORT_DIRECTIONS = {"asc", "desc"}


class MostRecentAttempt(BaseModel):
    session_id: UUID
    test_id: int
    test_name: str
    submitted_at: datetime
    score: Optional[float] = None


class UserSummary(BaseModel):
    """Summary envelope for GET /reports/user/{user_id}.

    Aggregates run over SUBMITTED sessions only — ACTIVE/EXPIRED attempts have
    no final score. Scores are percentages (per-answer [0, 1] fractions
    averaged per session, x100).
    """

    user_id: int
    total_attempts: int
    avg_score: Optional[float] = None
    best_score: Optional[float] = None
    total_time_seconds: Optional[float] = None
    most_recent: Optional[MostRecentAttempt] = None


class AttemptItem(BaseModel):
    session_id: UUID
    test_id: int
    test_name: str
    status: SessionStatus
    started_at: datetime
    submitted_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    score: Optional[float] = None


class AttemptsPage(BaseModel):
    items: List[AttemptItem]
    total: int
    page: int
    size: int


class AttemptsQuery(BaseModel):
    """Query-parameter dependency for GET /reports/user/{user_id}/attempts.

    ``from``/``to`` are exposed under their spec names via aliases (``from``
    is a Python keyword) and bound the attempt *start* time (``server_now``),
    which exists for every status — a ``submitted_at`` range would silently
    drop ACTIVE attempts. ``to`` is inclusive of the whole end date.
    """

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    test_id: Optional[int] = None
    date_from: Optional[date] = Field(None, alias="from")
    date_to: Optional[date] = Field(None, alias="to")
    status: Optional[SessionStatus] = None
    sort: str = "submitted_at:desc"

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: str) -> str:
        field, sep, direction = v.partition(":")
        if not sep or field not in SORT_FIELDS or direction not in SORT_DIRECTIONS:
            raise ValueError(
                "sort must be 'field:direction' with field in "
                f"{sorted(SORT_FIELDS)} and direction in {sorted(SORT_DIRECTIONS)}"
            )
        return v
