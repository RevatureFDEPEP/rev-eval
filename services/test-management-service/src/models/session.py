import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class Session(Base):
    """A quiz-taking session: server-authoritative timing + the fixed,
    ordered set of sampled question ids the candidate works through.

    Timing (server_now/expires_at) is recorded here, never by the client.
    question_ids is the ordered list of question-management-service Mongo
    _id strings sampled at creation; current_index indexes into it (advanced
    by W3-F2's answer endpoint).
    """

    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)  # participant id from X-User-Id

    # Opaque session token (secrets.token_hex) — not the UUID.
    session_token = Column(String(128), nullable=False, unique=True, index=True)

    # Server-authoritative timing (tz-naive UTC, matching repo convention).
    server_now = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
    current_index = Column(Integer, nullable=False, default=0)

    # Ordered list of sampled question ids (Mongo _id strings).
    question_ids = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
