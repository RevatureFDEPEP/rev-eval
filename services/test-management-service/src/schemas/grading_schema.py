"""Schemas for the trainer manual-grading flow (W5-F1).

A free-text answer is recorded ``PENDING_REVIEW`` at submit; a trainer lists the
queue (:class:`GradingQueueOut`) and grades one answer (:class:`GradeRequest` →
:class:`GradedAnswerOut`). The candidate's attempt score (computed on-read by the
reporting service) then includes the graded answer.
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GradeRequest(BaseModel):
    """Trainer's manual grade for one free-text answer."""

    score: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction in [0, 1] awarded to the answer"
    )
    feedback: Optional[str] = Field(
        None, description="Optional written feedback for the candidate"
    )


class PendingAnswerOut(BaseModel):
    """One free-text answer awaiting a manual grade, enriched with the question
    prompt + sample answer so a trainer can grade it without a second lookup."""

    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    session_id: UUID
    user_id: int
    question_index: int
    question_id: str
    submitted_answers: List[Any]
    submitted_at: Optional[datetime]
    test_id: int
    test_name: Optional[str] = None
    question_text: Optional[str] = None
    sample_answer: Optional[str] = None


class GradingQueueOut(BaseModel):
    """Paginated to-grade queue ({items, total, page, size} — W4 envelope)."""

    items: List[PendingAnswerOut]
    total: int
    page: int
    size: int


class GradedAnswerOut(BaseModel):
    """Result of grading one answer; ``session_needs_grading`` reflects whether
    the attempt still has ungraded free-text answers after this grade."""

    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    session_id: UUID
    question_index: int
    score: float
    is_correct: bool
    grading_status: str
    feedback: Optional[str]
    graded_by_id: Optional[int]
    graded_at: Optional[datetime]
    session_needs_grading: bool
