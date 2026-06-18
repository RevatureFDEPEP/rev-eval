import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String

from src.db.session import EvalAiBase


class SessionStatus(str, enum.Enum):
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class QuizSession(EvalAiBase):
    __tablename__ = "quiz_sessions"

    id = Column(String(36), primary_key=True)
    test_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    status = Column(Enum(SessionStatus), nullable=False)
    server_now = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
