from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from fastapi import Query
from pydantic import BaseModel

from src.models.quiz_session import SessionStatus


class MostRecentAttempt(BaseModel):
    session_id: str
    test_id: int
    submitted_at: Optional[datetime]
    score: Optional[float]


class UserSummary(BaseModel):
    user_id: int
    total_attempts: int
    avg_score: Optional[float]
    best_score: Optional[float]
    total_time_spent_seconds: Optional[float]
    most_recent_attempt: Optional[MostRecentAttempt]


class AttemptItem(BaseModel):
    session_id: str
    test_id: int
    status: str
    submitted_at: Optional[datetime]
    score: Optional[float]
    created_at: datetime


class PaginatedAttempts(BaseModel):
    items: list[AttemptItem]
    total: int
    page: int
    size: int


ALLOWED_SORT_FIELDS = {"submitted_at", "created_at"}


@dataclass
class AttemptsFilter:
    page: int = Query(1, ge=1)
    size: int = Query(20, ge=1, le=100)
    test_id: Optional[int] = Query(None)
    from_: Optional[date] = Query(None, alias="from")
    to: Optional[date] = Query(None)
    status: Optional[SessionStatus] = Query(None)
    sort: str = Query("submitted_at:desc")
