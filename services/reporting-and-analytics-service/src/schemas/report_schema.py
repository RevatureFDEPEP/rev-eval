from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class QueryParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = "avg_score"
    order: Literal["asc", "desc"] = "desc"


class AttemptsQueryParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    test_id: Optional[int] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    status: Optional[str] = None
    sort_by: str = "completed_at"
    order: Literal["asc", "desc"] = "desc"


class TestSummary(BaseModel):
    test_id: int
    test_name: str
    attempt_count: int
    avg_score: Optional[float]
    pass_rate: Optional[float]
    score_distribution: Optional[Dict[str, int]] = None


class AggregateReportResponse(BaseModel):
    total_tests: int
    page: int
    page_size: int
    tests: List[TestSummary]


class RankingEntry(BaseModel):
    rank: int
    user_id: int
    score: float
    completed_at: Optional[datetime]


class RankingsResponse(BaseModel):
    test_id: int
    page: int
    page_size: int
    rankings: List[RankingEntry]


class UserSessionEntry(BaseModel):
    session_id: str
    test_id: int
    test_name: str
    percentage_score: Optional[float]
    completed_at: Optional[datetime]
    status: str


class UserSummaryResponse(BaseModel):
    user_id: int
    total_attempts: int
    avg_score: Optional[float]
    best_score: Optional[float]
    total_time_spent_seconds: Optional[int]
    most_recent: Optional[UserSessionEntry]


class AttemptsResponse(BaseModel):
    user_id: int
    total: int
    page: int
    page_size: int
    attempts: List[UserSessionEntry]
