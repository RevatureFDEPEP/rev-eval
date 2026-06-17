import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    STARTED     = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED   = "SUBMITTED"
    EXPIRED     = "EXPIRED"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    # String(36) instead of PG UUID dialect type — works with SQLite in tests too
    id            = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    test_id       = Column(Integer, ForeignKey("tests.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("test_submissions.id"), nullable=True)
    user_id       = Column(Integer, nullable=False)
    status        = Column(Enum(SessionStatus), default=SessionStatus.STARTED, nullable=False)
    current_index = Column(Integer, default=0, nullable=False)
    question_ids  = Column(JSON, nullable=False)  # list[str] of MongoDB ObjectIds, ordered
    server_now    = Column(DateTime, nullable=False)
    expires_at    = Column(DateTime, nullable=False)
    submitted_at  = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test       = relationship("Test", lazy="select")
    submission = relationship("TestSubmission", lazy="select")
