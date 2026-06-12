from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuizSessionCreate(BaseModel):
    test_id: int
    submission_id: Optional[int] = None


class QuizQuestionOut(BaseModel):
    question_id: str
    question_type: str
    question_text: str
    options: Optional[List[Dict[str, Any]]] = None


class QuizSessionStartResponse(BaseModel):
    session_id: UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    status: str
    current_index: int
    question: QuizQuestionOut

    model_config = ConfigDict(from_attributes=True)
