from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from src.db.session import Base


def utc_now(_ctx=None):
    return datetime.now(timezone.utc)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False)
    quiz_session_id = Column(
        Integer,
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # sha256 of the canonical request body — distinguishes a genuine retry
    # (same hash -> replay) from key reuse with a different payload (-> 409).
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        UniqueConstraint("quiz_session_id", "key", name="uq_idempotency_session_key"),
    )
