import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SessionCreate(BaseModel):
    test_id: int


class SessionOut(BaseModel):
    session_id: uuid.UUID
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: dict[str, Any]

    class Config:
        from_attributes = True
