"""SQLAlchemy models for the server-authoritative quiz-taking slice.

Portable column types are used deliberately:

* ``session_id`` is a stringified uuid4 (``String(36)``) rather than a native
  Postgres ``UUID`` so the same models run unmodified against in-memory SQLite
  in the test suite while remaining correct on Postgres in production.
* JSON payloads use the dialect-neutral :class:`sqlalchemy.JSON` type, which
  maps to ``jsonb``/``json`` on Postgres and a serialized TEXT column on SQLite.

The full question (including answer keys) is snapshotted in
``QuizSessionQuestion.snapshot_json`` for server-side scoring and is NEVER
serialized to a participant; the participant-facing payload is built through
the safe ``QuizQuestionOut`` schema only.
"""
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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from src.db.session import Base


class SessionStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    expired = "expired"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # session_id is the public handle (uuid4 hex); generated in the service
    # layer so it is the single source of truth. The opaque session_token is a
    # separate unguessable secret returned to the client.
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(
        Integer,
        ForeignKey("test_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(64), unique=True, nullable=False)

    status = Column(
        Enum(SessionStatus, native_enum=False, length=16),
        nullable=False,
        default=SessionStatus.in_progress,
    )
    current_index = Column(Integer, nullable=False, default=0)

    # Autosaved draft: {question_id: [selected_answers]}. Server-bound so the
    # attempt survives a client crash / localStorage wipe.
    draft_answers = Column(JSON, nullable=False, default=dict)

    # Server-authoritative clock. expires_at is what the timer counts down to;
    # the client's local clock is never trusted for lock decisions.
    server_started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    # Final tally — populated only on submit / auto-submit.
    total_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    percentage_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    questions = relationship(
        "QuizSessionQuestion",
        cascade="all, delete-orphan",
        order_by="QuizSessionQuestion.question_index",
    )
    answers = relationship("QuizAnswer", cascade="all, delete-orphan")


class QuizSessionQuestion(Base):
    """Immutable per-session snapshot of one sampled question.

    Holds the FULL question payload (``snapshot_json``), including answer keys,
    so scoring is stable even if the question bank changes mid-session. This row
    is server-only and must never be serialized to a participant.
    """

    __tablename__ = "quiz_session_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_session_id = Column(
        Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)
    question_type = Column(String(32), nullable=False)
    snapshot_json = Column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "quiz_session_id", "question_index", name="uq_session_question_index"
        ),
    )


class QuizAnswer(Base):
    """The latest scored answer for one question within a session.

    One row per ``(quiz_session_id, question_index)`` — re-answering a question
    upserts this row. Scoring is server-authoritative; correctness is stored but
    only surfaced to participants after the session is submitted.
    """

    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    quiz_session_id = Column(
        Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)

    submitted_answers = Column(JSON, nullable=False, default=list)
    is_correct = Column(Boolean, nullable=False, default=False)
    earned = Column(Float, nullable=False, default=0.0)
    possible = Column(Float, nullable=False, default=0.0)
    algorithm = Column(String(32), nullable=False, default="exact_match")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "quiz_session_id", "question_index", name="uq_answer_session_question"
        ),
    )


class IdempotencyRecord(Base):
    """Idempotency ledger for answer submissions.

    Scoped to ``(quiz_session_id, idempotency_key)`` — never table-wide — so a
    key reused across sessions or users cannot replay another session's
    response. ``request_fingerprint`` is a hash of the request payload: a retry
    with the same key + same payload replays ``response_payload``; the same key
    + a different payload is rejected (409).
    """

    __tablename__ = "quiz_idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    quiz_session_id = Column(
        Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key = Column(String(128), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    response_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "quiz_session_id", "idempotency_key", name="uq_idem_session_key"
        ),
    )
