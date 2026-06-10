from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base


class IdempotencyKey(Base):
    """Dedup record for a client-supplied ``Idempotency-Key`` (W3-F2).

    Scoped to a session: on the first successful answer submission the response
    (status + body) is stored here keyed by (session_id, idempotency_key); a
    retry with the same key replays the stored response without re-scoring or
    re-advancing the session.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "idempotency_key", name="uq_idempotency_session_key"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(128), nullable=False)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False
    )
    status_code = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
