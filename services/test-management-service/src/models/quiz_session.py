import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.types import JSON

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class QuizSessionStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class QuizSession(Base):
    """
    A participant's live quiz attempt.

    Standalone (keyed by test_id + user_id), independent of TestSubmission.
    Timing is server-authoritative: started_at is the server anchor and
    expires_at is computed server-side from the test duration. The ordered
    set of question IDs is frozen at creation so navigation and scoring see a
    stable question set.
    """

    __tablename__ = "quiz_sessions"

    # uuid4 string PK (String(36) for cross-DB portability; SQLite has no UUID type)
    session_id = Column(String(36), primary_key=True, index=True)

    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    user_id = Column(
        Integer, nullable=False, index=True
    )  # participant (external user id)

    session_token = Column(String(64), nullable=False, unique=True, index=True)

    # Frozen ordered list of Mongo ObjectId strings (JSON, not ARRAY, for SQLite)
    question_ids = Column(JSON, nullable=False)
    current_index = Column(Integer, nullable=False, default=0)

    # Advisory autosave snapshot of in-progress selections (question_id -> option_ids).
    # Last-write-wins, never scored, does not advance current_index or change status.
    # Read back on resume to rehydrate the client's answer map (W3-F4).
    draft_answers = Column(JSON, nullable=True)

    status = Column(
        Enum(QuizSessionStatus), nullable=False, default=QuizSessionStatus.ACTIVE
    )

    # Server-authoritative timing (naive UTC, matching repo convention)
    created_at = Column(DateTime, default=_utcnow)
    started_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
