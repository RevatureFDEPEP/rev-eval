from datetime import datetime
from typing import List, Optional

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
