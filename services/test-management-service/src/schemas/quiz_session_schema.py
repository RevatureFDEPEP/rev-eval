# src/schemas/quiz_session_schema.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum


class SessionStatus(str, Enum):
    STARTED = "STARTED"
    PART_A_IN_PROGRESS = "PART_A_IN_PROGRESS"
    PART_A_COMPLETED = "PART_A_COMPLETED"
    PART_B_IN_PROGRESS = "PART_B_IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class DraftSaveIn(BaseModel):
    answers: List[Any]

    class Config:
        from_attributes = True


class PartAConfig(BaseModel):
    easy: int = 3
    medium: int = 4
    hard: int = 4

    class Config:
        from_attributes = True


class QuizSessionCreate(BaseModel):
    """Maps to frontend TestSessionCreate."""
    test_id: int
    submission_id: int
    user_id: int
    total_questions: Optional[int] = 20
    part_a_config: Optional[PartAConfig] = None

    class Config:
        from_attributes = True


class QuizAnswerIn(BaseModel):
    """A single answered question."""
    question_id: str
    selected_answers: List[int]

    class Config:
        from_attributes = True


class PartASubmitIn(BaseModel):
    """Body for POST /{session_id}/part-a/submit."""
    session_id: str
    answers: List[QuizAnswerIn]

    class Config:
        from_attributes = True


class PartBSubmitIn(BaseModel):
    """Body for POST /{session_id}/part-b/submit."""
    session_id: str
    answers: List[QuizAnswerIn]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class QuizOptionOut(BaseModel):
    option_id: int
    text: str

    class Config:
        from_attributes = True


class QuizQuestionOut(BaseModel):
    """Safe question view — correct_answer/correct_answers are NEVER included."""
    question_id: str
    question_text: str
    question_type: str
    difficulty: str
    options: Optional[List[QuizOptionOut]] = None

    class Config:
        from_attributes = True


class PartAQuestionsOut(BaseModel):
    session_id: str
    questions: List[QuizQuestionOut]
    total_questions: int
    time_limit_minutes: Optional[int] = None

    class Config:
        from_attributes = True


class PartBQuestionsOut(BaseModel):
    session_id: str
    questions: List[QuizQuestionOut]
    total_questions: int
    time_limit_minutes: Optional[int] = None
    ai_message: Optional[str] = None

    class Config:
        from_attributes = True


class QuizSubmitOut(BaseModel):
    score: float
    total_questions: int
    correct_answers: float
    analysis: Optional[str] = None

    class Config:
        from_attributes = True


class QuizSessionOut(BaseModel):
    """Maps to frontend TestSession."""
    id: str
    test_id: int
    submission_id: int
    user_id: int
    status: SessionStatus
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_questions: int
    part_a_config: Optional[Any] = None
    part_b_config: Optional[Any] = None
    part_a: Optional[Any] = None
    part_b: Optional[Any] = None
    draft_answers: Optional[Any] = None
    total_score: Optional[float] = None
    percentage_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionStatusOut(BaseModel):
    """Minimal status check response."""
    session_id: str
    status: SessionStatus
    current_part: Optional[str] = None

    class Config:
        from_attributes = True
