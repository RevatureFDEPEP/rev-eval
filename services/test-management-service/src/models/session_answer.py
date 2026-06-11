from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SessionAnswer(Base):
    """One scored answer submitted by a participant during a quiz session."""

    __tablename__ = "session_answers"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "idempotency_key",
            name="uq_session_answer_idempotency",
        ),
        # One scored answer per question per session — the durable backstop
        # against double-scoring when no Idempotency-Key is sent or a row lock
        # is unavailable (e.g. SQLite).
        UniqueConstraint(
            "session_id",
            "question_index",
            name="uq_session_answer_question_index",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("quiz_sessions.session_id"),
        nullable=False,
        index=True,
    )
    question_id = Column(String, nullable=False)
    question_index = Column(Integer, nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    points_earned = Column(Float, nullable=False)
    max_points = Column(Float, nullable=False, default=1.0)
    requires_manual_review = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
