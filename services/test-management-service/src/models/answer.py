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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base


class Answer(Base):
    """One scored answer within a quiz session (W3-F2).

    Recorded server-side after scoring the question at ``question_index`` in the
    session's ordered ``question_ids``. ``score`` is a fraction in [0, 1]
    (partial-credit aware); ``is_correct`` is reserved for a perfect answer.
    The unique (session_id, question_index) constraint enforces one scored row
    per slot — a backstop alongside the pessimistic lock + idempotency key.
    """

    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_index", name="uq_answer_session_index"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False
    )
    question_id = Column(String, nullable=False)  # Mongo _id of the scored question
    question_index = Column(Integer, nullable=False)
    submitted_answers = Column(JSON, nullable=False, default=list)
    score = Column(Float, nullable=False, default=0.0)
    is_correct = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
