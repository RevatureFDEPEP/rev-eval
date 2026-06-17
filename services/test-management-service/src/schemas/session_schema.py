import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SessionCreate(BaseModel):
    test_id: int


class SessionOut(BaseModel):
    session_id: uuid.UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: dict[str, Any]

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: str
    submitted_answers: list[str]


class AnswerResponse(BaseModel):
    question_id: str
    earned_points: float
    max_points: float
    is_correct: bool
    next_question: dict[str, Any] | None
    session_status: str
    current_index: int
