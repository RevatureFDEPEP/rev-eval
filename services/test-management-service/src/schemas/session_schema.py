from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from src.models.session import SessionStatus


class SessionCreate(BaseModel):
    test_id: int


class SessionOut(BaseModel):
    session_id: str
    test_id: int
    user_id: int
    session_token: str
    server_now: datetime
    expires_at: datetime
    status: SessionStatus
    current_index: int

    class Config:
        from_attributes = True


class SessionStartResponse(BaseModel):
    """Response body for POST /sessions — all timing state lives server-side."""

    session_id: str
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: Optional[Dict[str, Any]] = None
    questions: List[Dict[str, Any]] = []


class AnswerSubmit(BaseModel):
    """Request body for POST /sessions/{id}/answer."""
    submitted_answers: List[Any]


class AnswerResponse(BaseModel):
    """Response body for POST /sessions/{id}/answer."""
    session_id: str
    question_id: str
    score: float
    is_correct: bool
    points_earned: float
    points_possible: float
    details: str
    current_index: int
    session_status: SessionStatus
    next_question: Optional[Dict[str, Any]] = None
    submitted_at: Optional[datetime] = None
