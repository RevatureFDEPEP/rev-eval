# src/models/answer.py
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class QuizAnswer(Base):
    """One scored answer within a quiz session (W3-F2).

    Doubles as the idempotency ledger: ``idempotency_key`` is uniquely indexed
    and ``response_payload`` stores the exact response returned the first time a
    key was seen, so a retried POST replays that response without re-scoring or
    re-advancing the session. ``question_id`` is the MongoDB ``_id`` string of
    the answered question; ``question_index`` is its position in the session's
    ``question_ids`` snapshot at the time it was answered.
    """

    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String(36), ForeignKey("sessions.session_id"), nullable=False, index=True
    )
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)

    submitted_answers = Column(JSON, nullable=False, default=list)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    algorithm = Column(String(32), nullable=False)

    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    response_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("QuizSession")
