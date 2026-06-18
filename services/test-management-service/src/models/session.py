import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    SUBMITTED = "SUBMITTED"


class Session(Base):
    __tablename__ = "sessions"

    # UUID stored as String(36) for cross-database compatibility (PostgreSQL + SQLite tests)
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(128), nullable=False, unique=True)
    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
    current_index = Column(Integer, nullable=False, default=0)
    # Ordered list of question IDs sampled at session creation
    question_ids = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test = relationship("Test", back_populates="sessions")
