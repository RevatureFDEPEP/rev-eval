# src/models/session.py
import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class SessionStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class QuizSession(Base):
    """A live quiz-taking session: a snapshot of sampled questions plus the
    server-authoritative clock the participant races against.

    ``session_id`` is a stringified uuid4 (String(36) PK, not a native pg UUID —
    SQLAlchemy 1.4.7 here has no ``Uuid`` type). ``question_ids`` is the ordered
    snapshot of sampled question IDs so ``current_index`` maps to a stable set
    even if the bank changes mid-session (consumed by W3-F2 scoring).
    """

    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    session_token = Column(String(64), nullable=False)

    server_now = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
    current_index = Column(Integer, nullable=False, default=0)
    question_ids = Column(JSON, nullable=False, default=list)

    # Set when the final question is answered (status -> SUBMITTED). NULL while
    # the session is still ACTIVE or was EXPIRED before completion (W3-F2).
    submitted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test = relationship("Test")
