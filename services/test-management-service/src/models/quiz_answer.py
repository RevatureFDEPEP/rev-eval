from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from src.db.session import Base


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    quiz_session_id = Column(
        Integer,
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)
    submitted_answers = Column(JSON, nullable=False)
    earned = Column(Float, nullable=False)
    possible = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # One scored answer per question per session — guards against double-scoring.
    __table_args__ = (
        UniqueConstraint("quiz_session_id", "question_index", name="uq_answer_session_index"),
    )
