# src/schemas/answer_schema.py
from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

from src.models.session import SessionStatus
from src.schemas.session_schema import SanitizedQuestion


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
    """Post-advance session state after scoring one answer.

    Deliberately **score-free**: per-question ``is_correct``/``score`` are
    computed and persisted server-side (``quiz_answers``) but NOT returned, so
    correctness is never disclosed to the candidate mid-exam. Forward motion is
    driven by ``next_question`` (sequential reveal); it is ``None`` once the
    final question is answered and ``status`` becomes ``SUBMITTED``.
    """

    question_id: str = Field(..., description="Id of the question just answered")
    current_index: int = Field(..., description="Index advanced past the answered question")
    total_questions: int
    status: SessionStatus
    submitted_at: datetime | None = Field(
        None, description="Set once the session is finalized (final question answered)"
    )
    next_question: SanitizedQuestion | None = Field(
        None, description="Next question body (answer key stripped); None when finished"
    )
