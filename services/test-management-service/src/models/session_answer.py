from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from src.db.session import Base


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)
    question_type = Column(String(32), nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    correct_answers = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
