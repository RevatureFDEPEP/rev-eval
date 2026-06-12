# src/schemas/answer_schema.py
from typing import Union

from pydantic import BaseModel, Field

from src.models.session import SessionStatus


class AnswerCreate(BaseModel):
    """Request body for submitting an answer to the session's current question.

    ``submitted_answers`` mirrors question-management-service's answer shape:
    1-indexed option positions (int) for MCQ/MULTI, a single bool for
    TRUE_FALSE. ``question_id`` is optional; when supplied it is checked against
    the session's current question to reject out-of-order/stale submissions.
    """

    submitted_answers: list[Union[int, bool, str]] = Field(default_factory=list)
    question_id: str | None = None


class AnswerResponse(BaseModel):
    """Result of scoring one answer plus the post-advance session state."""

    is_correct: bool
    score: float
    algorithm: str
    current_index: int
    status: SessionStatus
    finished: bool = Field(
        ..., description="True once the final question was answered (status SUBMITTED)"
    )
