"""Pydantic schemas for the quiz-taking slice.

Participant-facing schemas (``QuizQuestionOut``, ``QuizSessionStartResponse``,
``QuizSessionStateResponse``, ``AnswerResultResponse``) deliberately omit answer
keys and per-question correctness. Aggregate scoring is only surfaced by
``QuizSubmitResponse`` once the session is finalized.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# A single selected option: an option index (int) or a boolean for true/false.
SelectedAnswer = Union[int, bool]


class QuizSessionCreate(BaseModel):
    test_id: int
    submission_id: Optional[int] = None


class QuizQuestionOut(BaseModel):
    """Safe, participant-facing question view — never includes answer keys."""

    question_id: str
    question_index: int
    question_type: str
    question_text: str
    options: Optional[List[Dict[str, Any]]] = None


class QuizSessionStartResponse(BaseModel):
    session_id: str
    session_token: str
    server_now: datetime
    expires_at: datetime
    status: str
    current_index: int
    total_questions: int
    question: QuizQuestionOut

    model_config = ConfigDict(from_attributes=True)


class QuizSessionStateResponse(BaseModel):
    """Full session state for resume/refresh — all questions, safe view."""

    session_id: str
    status: str
    server_now: datetime
    expires_at: datetime
    current_index: int
    total_questions: int
    draft_answers: Dict[str, List[SelectedAnswer]] = Field(default_factory=dict)
    questions: List[QuizQuestionOut]
    # Populated only once the session is submitted.
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    percentage_score: Optional[float] = None


class DraftPatch(BaseModel):
    """Autosave payload. Both fields optional so a save can update either the
    cursor position or the buffered answers independently."""

    current_index: Optional[int] = None
    answers: Optional[Dict[str, List[SelectedAnswer]]] = None


class DraftResponse(BaseModel):
    session_id: str
    status: str
    server_now: datetime
    expires_at: datetime
    current_index: int
    draft_answers: Dict[str, List[SelectedAnswer]] = Field(default_factory=dict)


class AnswerSubmit(BaseModel):
    question_id: str
    selected_answers: List[SelectedAnswer] = Field(default_factory=list)


class AnswerResultResponse(BaseModel):
    """Acknowledges a recorded answer WITHOUT leaking correctness.

    Per-question correctness is intentionally absent — the participant only
    learns aggregate results after submitting the whole session.
    """

    session_id: str
    question_id: str
    recorded: bool
    answered_count: int
    total_questions: int
    server_now: datetime
    expires_at: datetime


class QuizSubmitResponse(BaseModel):
    session_id: str
    status: str
    submitted_at: datetime
    total_score: float
    max_score: float
    percentage_score: float
    correct_count: int
    answered_count: int
    total_questions: int
