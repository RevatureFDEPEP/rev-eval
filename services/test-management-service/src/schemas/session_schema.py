from datetime import datetime

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    quiz_id: int


class QuestionOut(BaseModel):
    id: str
    type: str
    question_text: str
    options: list[dict] | None = None
    difficulty: str | None = None
    skills: list[str] = []
    tags: list[str] = []


class SessionResponse(BaseModel):
    session_token: str
    submission_id: int
    test_id: int
    server_now: datetime
    expires_at: datetime
    total_questions: int
    current_position: int
    first_question: QuestionOut | None = None

    class Config:
        from_attributes = True
