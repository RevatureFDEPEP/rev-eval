import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String

from src.db.session import Base


class AttemptStatus(str, enum.Enum):
    """Mirror of test-management's SessionStatus (see ADR 0001)."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    SUBMITTED = "SUBMITTED"


class SessionMirror(Base):
    """Denormalized, read-optimized projection of a quiz attempt (session).

    Populated by an event projection from test-management-service; this service
    only ever reads from this table. One row == one attempt.
    """

    __tablename__ = "session_mirror"

    # UUID stored as String(36) for cross-database compatibility (Postgres + SQLite).
    session_id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    # test_id kept as String so it can be filtered as an opaque identifier.
    test_id = Column(String(64), nullable=True, index=True)
    status = Column(Enum(AttemptStatus), nullable=False, default=AttemptStatus.ACTIVE)
    score = Column(Float, nullable=False, default=0.0)
    time_spent_seconds = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
