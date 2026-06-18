from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON

from src.db.session import Base


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    earned_points = Column(Float, nullable=False)
    max_points = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("session_id", "question_index", name="uq_session_answer_index"),)
