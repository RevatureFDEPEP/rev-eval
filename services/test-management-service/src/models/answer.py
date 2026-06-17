import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base


class GradingStatus(str, enum.Enum):
    """Manual-grading lifecycle of an answer (W5-F1).

    ``AUTO`` — auto-scored at submit (mcq/true_false/multi); final.
    ``PENDING_REVIEW`` — non-auto-scorable (free text); awaiting a trainer and
    excluded from the attempt score until graded.
    ``GRADED`` — a trainer has set the score/feedback; counts toward the score.
    """

    AUTO = "AUTO"
    PENDING_REVIEW = "PENDING_REVIEW"
    GRADED = "GRADED"


class Answer(Base):
    """One scored answer within a quiz session (W3-F2).

    Recorded server-side after scoring the question at ``question_index`` in the
    session's ordered ``question_ids``. ``score`` is a fraction in [0, 1]
    (partial-credit aware); ``is_correct`` is reserved for a perfect answer.
    The unique (session_id, question_index) constraint enforces one scored row
    per slot — a backstop alongside the pessimistic lock + idempotency key.

    ``grading_status`` (W5-F1) distinguishes auto-scored answers from free-text
    answers awaiting a trainer's manual grade; ``PENDING_REVIEW`` rows are
    excluded from the attempt score until graded.
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

    # Manual-grading lifecycle (W5-F1).
    grading_status = Column(
        Enum(GradingStatus),
        nullable=False,
        default=GradingStatus.AUTO,
        server_default=GradingStatus.AUTO.value,
    )
    feedback = Column(Text, nullable=True)  # optional trainer feedback on a grade
    graded_by_id = Column(Integer, nullable=True)  # trainer user id (X-User-Id)
    graded_at = Column(DateTime, nullable=True)
