from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class SessionCreate(BaseModel):
    test_id: int
    submission_id: Optional[int] = None


class QuizQuestionOut(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    difficulty: str
    options: Optional[List[dict]] = None
    # correct_answers intentionally absent — never sent to client during a live quiz


class SessionRead(BaseModel):
    session_id: str
    session_token: str
    test_id: int
    user_id: int
    status: str
    current_index: int
    server_now: datetime
    expires_at: datetime
    first_question: Optional[QuizQuestionOut]

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: str
    submitted_answers: List[Union[int, bool, str]]


class AnswerResponse(BaseModel):
    session_id: str
    question_id: str
    question_index: int
    score: Optional[float]
    algorithm: str
    session_status: str
    current_index: int
    next_question: Optional[QuizQuestionOut]
