"""Pydantic schemas for the reporting endpoints (W4-F1 user results,
W4-F3 trainer aggregates)."""
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


class AggregateQuery(BaseModel):
    """Query-parameter dependency for GET /reports/aggregate (W4-F3).

    Same ``from``/``to`` alias + attempt-start semantics as AttemptsQuery.
    ``min_attempts`` becomes a HAVING clause — tests with fewer submitted
    attempts are dropped from the report.
    """

    model_config = ConfigDict(populate_by_name=True)

    test_id: Optional[int] = None
    date_from: Optional[date] = Field(None, alias="from")
    date_to: Optional[date] = Field(None, alias="to")
    min_attempts: Optional[int] = Field(None, ge=1)


class TestAggregateRow(BaseModel):
    """Per-test aggregate over SUBMITTED sessions. ``pass_rate`` is the
    percentage of attempts scoring at or above the configured threshold."""

    test_id: int
    test_name: str
    total_attempts: int
    distinct_candidates: int
    avg_score: Optional[float] = None
    pass_rate: Optional[float] = None
    median_duration_seconds: Optional[float] = None


class AggregateReport(BaseModel):
    items: List[TestAggregateRow]
    pass_threshold: float


class ScoreHistogram(BaseModel):
    bucket_0_25: int = Field(..., description="answers with score in [0, 0.25)")
    bucket_25_50: int = Field(..., description="answers with score in [0.25, 0.5)")
    bucket_50_75: int = Field(..., description="answers with score in [0.5, 0.75)")
    bucket_75_100: int = Field(..., description="answers with score in [0.75, 1]")


class QuestionDifficultyRow(BaseModel):
    """Per-question difficulty for one test. ``difficulty_rank`` 1 = hardest
    (lowest correct-answer rate); ``histogram`` counts answers per score
    bucket over the [0, 1] partial-credit fraction."""

    question_id: str
    attempts: int
    correct_rate: float
    difficulty_rank: int
    histogram: ScoreHistogram


class QuestionDifficultyReport(BaseModel):
    test_id: int
    test_name: str
    items: List[QuestionDifficultyRow]
