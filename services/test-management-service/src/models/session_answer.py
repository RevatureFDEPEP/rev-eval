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
from src.db.session import Base


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(128), nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    is_correct = Column(Boolean, nullable=False, default=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
