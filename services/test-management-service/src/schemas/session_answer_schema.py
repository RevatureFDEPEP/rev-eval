from typing import Any

from pydantic import BaseModel

from src.models.quiz_session import QuizSessionStatus
from src.schemas.quiz_session_schema import OptionalUtcDatetime, ParticipantQuestion


class AnswerSubmitRequest(BaseModel):
    question_id: str
    submitted_answers: list[Any]


class AnswerResult(BaseModel):
    question_id: str
    question_index: int
    is_correct: bool
    points_earned: float
    max_points: float
    requires_manual_review: bool
    session_status: QuizSessionStatus
    current_index: int
    total_questions: int
    question: (
        ParticipantQuestion | None
    )  # next question; None when session is submitted
    submitted_at: OptionalUtcDatetime = None
