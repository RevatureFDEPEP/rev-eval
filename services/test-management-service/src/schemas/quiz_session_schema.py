from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    quiz_id: int


class SessionResponse(BaseModel):
    session_token: str
    quiz_id: int
    user_id: int
    server_now: datetime
    expires_at: datetime
    first_question: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True