from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    """Request body for POST /sessions."""
    test_id: int = Field(..., description="ID of the quiz/test to start a session for")


class SanitizedQuestion(BaseModel):
    """A question as exposed to the candidate — answer fields are stripped.

    correct_answers and sample_answer are deliberately omitted so the client
    (and the initial HTML) never carry the answer key. Scoring happens
    server-side in W3-F2.
    """
    id: str
    type: str
    question_text: str
    options: Optional[List[dict]] = None
    difficulty: Optional[str] = None
    image_url: Optional[str] = None


class SessionOut(BaseModel):
    """Response contract for POST /sessions (consumed server-side by W3-F3).

    The client never computes or stores timing — server_now/expires_at are
    authoritative.
    """
    session_id: UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    current_index: int
    total_questions: int
    question: Optional[SanitizedQuestion] = None

    model_config = ConfigDict(from_attributes=True)
