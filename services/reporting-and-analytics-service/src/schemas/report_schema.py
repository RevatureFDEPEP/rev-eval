from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class AttemptItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    test_id: int
    user_id: int
    status: SessionStatus
    server_now: datetime
    submitted_at: Optional[datetime]
    expires_at: datetime
    score_ratio: Optional[float]


class UserSummaryResponse(BaseModel):
    user_id: int
    total_attempts: int
    average_score: Optional[float]
    best_score: Optional[float]
    total_time_spent: Optional[float]
    most_recent_attempt: Optional[AttemptItem]


class PaginatedAttemptsResponse(BaseModel):
    items: list[AttemptItem]
    total: int
    page: int
    size: int


@dataclass
class AttemptFilter:
    page: int = field(default=1)
    size: int = field(default=20)
    test_id: Optional[int] = field(default=None)
    from_date: Optional[date] = field(default=None)
    to_date: Optional[date] = field(default=None)
    status: Optional[SessionStatus] = field(default=None)
    sort: str = field(default="server_now:desc")
