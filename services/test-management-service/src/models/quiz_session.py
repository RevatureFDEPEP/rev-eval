# src/models/quiz_session.py
"""QuizSession ORM model (W3-F1, Part B).

A quiz session is the server-authoritative record minted when a candidate
starts a quiz: it pins the exact ordered set of question ids the candidate
will see, an opaque session token, and a server-computed expiry. The client
displays a countdown from ``server_now``/``expires_at`` but never decides
acceptance — every later mutation re-checks the clock against ``expires_at``.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from src.db.session import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now (never naive ``utcnow``) so the persisted
    anchors carry an explicit offset and countdown math stays unambiguous."""
    return datetime.now(UTC)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    # Opaque UUID hex string PK — safe to expose in URLs/logs (it identifies,
    # it does not authenticate; the session_token authenticates).
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)

    # Opaque bearer token for the session (minted with secrets.token_hex).
    session_token = Column(String(128), nullable=False)

    # The test this session was started from.
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)

    # Optional link back to an assigned submission row.
    submission_id = Column(Integer, ForeignKey("test_submissions.id"), nullable=True)

    # The candidate (resolved from the verified gateway identity, never the body).
    user_id = Column(Integer, nullable=False, index=True)

    # The frozen, ordered list of sampled question ids (JSON array of str).
    question_ids = Column(JSON, nullable=False, default=list)

    # Server-authoritative clock anchors (timezone-aware so the countdown the
    # client renders is anchored to an explicit UTC offset, not a naive value).
    server_now = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Lifecycle.
    status = Column(String(32), nullable=False, default="in_progress")
    current_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
