import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum as SAEnum, ForeignKey

from src.db.session import Base
import enum


class SessionStatus(str, enum.Enum):
    STARTED = "STARTED"
    PART_A_IN_PROGRESS = "PART_A_IN_PROGRESS"
    PART_A_COMPLETED = "PART_A_COMPLETED"
    PART_B_IN_PROGRESS = "PART_B_IN_PROGRESS"
    PART_B_COMPLETED = "PART_B_COMPLETED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    ABANDONED = "ABANDONED"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # nullable after migration 0002 — scoring engine route does not issue tokens
    token_hash = Column(String(64), nullable=True, unique=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("test_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.STARTED)

    server_now = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    total_questions = Column(Integer, default=20)
    part_a_config = Column(JSON, default=lambda: {"easy": 3, "medium": 4, "hard": 4})
    part_b_config = Column(JSON, default=lambda: {"easy": 3, "medium": 4, "hard": 4})

    part_a = Column(JSON, nullable=True)
    part_b = Column(JSON, nullable=True)
    draft_answers = Column(JSON, nullable=True)

    part_a_score = Column(Float, nullable=True)
    part_b_score = Column(Float, nullable=True)
    total_score = Column(Float, nullable=True)
    percentage_score = Column(Float, nullable=True)

    # Idempotency: SHA-256 hash of Idempotency-Key header value
    part_a_idempotency_hash = Column(String(64), nullable=True)
    part_b_idempotency_hash = Column(String(64), nullable=True)
    part_a_response_cache = Column(JSON, nullable=True)
    part_b_response_cache = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
