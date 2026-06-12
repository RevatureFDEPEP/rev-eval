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
    GRADED = "GRADED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # SHA-256 hex digest of secrets.token_urlsafe(32) — raw token is never stored
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("test_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(SAEnum(SessionStatus), nullable=False, default=SessionStatus.STARTED)

    # server_now: UTC timestamp recorded at creation — client uses this as clock reference
    server_now = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    total_questions = Column(Integer, default=20)
    part_a_config = Column(JSON, default=lambda: {"easy": 3, "medium": 4, "hard": 4})
    part_b_config = Column(JSON, default=lambda: {"easy": 3, "medium": 4, "hard": 4})

    # Stored as {questions: [...], answers: [...], score: float, total_questions: int}
    part_a = Column(JSON, nullable=True)
    part_b = Column(JSON, nullable=True)

    total_score = Column(Float, nullable=True)
    percentage_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
