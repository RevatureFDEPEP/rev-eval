from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class AnswerSubmit(BaseModel):
    session_token: str
    question_id: str
    # Capped to bound payload size — far above any real option count (multi
    # allows up to 10 options; true/false and single-select need 1).
    answers: List[Union[int, bool, str]] = Field(..., max_length=50)


class AnswerAck(BaseModel):
    """Answer-submission acknowledgement.

    Intentionally omits per-question correctness/score: that is recorded
    server-side only so candidates cannot brute-force answers mid-test.
    """

    question_id: str
    recorded: bool
    current_index: int
    status: str
    finished: bool
    next_question: Optional[QuizQuestionOut] = None
