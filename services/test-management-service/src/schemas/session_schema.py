from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel
from src.models.session import SessionStatus


class SessionCreate(BaseModel):
    test_id: int


class SessionOut(BaseModel):
    session_id: str
    test_id: int
    user_id: int
    session_token: str
    server_now: datetime
    expires_at: datetime
    status: SessionStatus
    current_index: int

    class Config:
        from_attributes = True


class SessionStartResponse(BaseModel):
    """Response body for POST /sessions — all timing state lives server-side."""
    session_id: str
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: Optional[Dict[str, Any]] = None
