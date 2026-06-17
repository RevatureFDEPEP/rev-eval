# src/schemas/reports_schema.py
"""Pydantic schemas for the candidate reporting endpoints (W4-F1).

Scores are PERCENTAGES: per-answer scores are [0, 1] fractions, averaged per
session and multiplied by 100, so the API returns 0..100 and the frontend
renders them directly.
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.tms_readonly import SessionStatus

SORT_FIELDS = {"submitted_at", "created_at", "score"}
SORT_DIRECTIONS = {"asc", "desc"}


class MostRecentAttempt(BaseModel):
    session_id: str
    test_id: int
    test_name: str | None = None
    status: SessionStatus
    submitted_at: datetime | None = None
    score: float | None = Field(None, description="Attempt score 0..100")


class UserSummary(BaseModel):
    """Summary envelope for GET /reports/user/{user_id}.

    Aggregates run over SUBMITTED sessions only — ACTIVE/EXPIRED attempts have
    no final score. Scores are percentages (0..100)."""

    user_id: int
    total_attempts: int
    avg_score: float | None = None
    best_score: float | None = None
    total_time_seconds: float | None = None
    most_recent: MostRecentAttempt | None = None


class AttemptItem(BaseModel):
    session_id: str
    test_id: int
    test_name: str | None = None
    status: SessionStatus
    questions_answered: int
    started_at: datetime
    submitted_at: datetime | None = None
    duration_seconds: float | None = None
    score: float | None = Field(None, description="Final attempt score 0..100; null until SUBMITTED")


class AttemptsPage(BaseModel):
    items: list[AttemptItem]
    total: int
    page: int
    size: int


class AttemptsQuery(BaseModel):
    """Query-parameter dependency for GET /reports/user/{user_id}/attempts.

    ``from``/``to`` are exposed under their spec names via aliases (``from`` is
    a Python keyword) and bound the attempt *start* time (``server_now``),
    which exists for every status — a ``submitted_at`` range would silently
    drop ACTIVE attempts. ``to`` is inclusive of the whole end date. ``sort`` is
    ``field:direction`` whitelisted to {submitted_at, created_at, score}."""

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    test_id: int | None = None
    date_from: date | None = Field(None, alias="from")
    date_to: date | None = Field(None, alias="to")
    status: SessionStatus | None = None
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
