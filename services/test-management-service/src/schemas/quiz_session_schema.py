from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.models.quiz_session import SessionStatus


class PartConfig(BaseModel):
    easy: int = 3
    medium: int = 4
    hard: int = 4


class QuizSessionCreate(BaseModel):
    test_id: int
    submission_id: int
    user_id: int
    total_questions: Optional[int] = 20
    part_a_config: Optional[PartConfig] = None
    duration_seconds: Optional[int] = None


class PartData(BaseModel):
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    score: Optional[float] = None
    total_questions: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QuizSessionOut(BaseModel):
    id: str
    session_id: str           # alias for id — matches frontend expectation
    test_id: int
    submission_id: int
    user_id: int
    status: SessionStatus
    server_now: datetime
    started_at: datetime
    expires_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: int
    part_a_config: Optional[Dict[str, Any]] = None
    part_b_config: Optional[Dict[str, Any]] = None
    part_a: Optional[Dict[str, Any]] = None
    part_b: Optional[Dict[str, Any]] = None
    total_score: Optional[float] = None
    percentage_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    current_part: Optional[str] = None   # "A" | "B" | null — derived from status

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Any) -> "QuizSessionOut":
        data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        data["session_id"] = data["id"]
        # Derive current_part from status
        status = data["status"]
        if status in (SessionStatus.PART_A_IN_PROGRESS, SessionStatus.STARTED):
            data["current_part"] = "A"
        elif status in (SessionStatus.PART_B_IN_PROGRESS, SessionStatus.PART_A_COMPLETED):
            data["current_part"] = "B"
        else:
            data["current_part"] = None
        return cls(**data)


class QuizSessionCreateResponse(QuizSessionOut):
    # Opaque token returned ONCE at creation — client stores for auth on submit
    token: str


class PartAQuestionsResponse(BaseModel):
    session_id: str
    questions: List[Dict[str, Any]]
    total_questions: int
    time_limit_minutes: Optional[int] = None


class PartBQuestionsResponse(BaseModel):
    session_id: str
    questions: List[Dict[str, Any]]
    total_questions: int
    time_limit_minutes: Optional[int] = None
    ai_message: Optional[str] = None


class QuizAnswer(BaseModel):
    question_id: str
    selected_answers: List[int] = Field(default_factory=list)
    time_spent_seconds: Optional[int] = None


class PartASubmit(BaseModel):
    session_id: str
    answers: List[QuizAnswer]


class PartBSubmit(BaseModel):
    session_id: str
    answers: List[QuizAnswer]


class QuizSubmitResponse(BaseModel):
    score: float
    total_questions: int
    correct_answers: int
    analysis: Optional[str] = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    current_part: Optional[str] = None
