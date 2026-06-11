# src/schemas/session_schema.py
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for starting a quiz session."""
    test_id: int


class SessionResponse(BaseModel):
    """Response contract for a freshly created quiz session (W3-F1 spec line 50).

    ``first_question`` is the body of the first sampled question as returned by
    question-management-service (kept as a raw dict so the contract is decoupled
    from that service's response schema). It is ``None`` only if the bank is
    empty.
    """
    session_id: str
    session_token: str
    server_now: datetime
    expires_at: datetime
    first_question: dict | None = Field(
        None, description="Body of the first sampled question (from question-management-service)"
    )
