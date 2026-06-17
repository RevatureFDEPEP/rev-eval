import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from src.db.session import Base


class SessionStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(36), unique=True, nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("test_submissions.id"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    first_question_id = Column(String(24), nullable=True)
    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
    current_position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
