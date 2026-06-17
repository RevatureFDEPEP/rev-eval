"""Read-only mapped copies of test-management-service tables.

These tables live in test-management-service's Postgres (``eval_ai_dev``) and
are owned by that service's Alembic chain — this service only ever SELECTs from
them, over the dedicated ``tms_engine`` / ``get_tms_db`` in src/db/session.py.
See docs/adr/0001-reporting-cross-service-data-access.md.

Containment rules:
- Every TMS mapping lives here on ``TmsBase`` — never on the reporting ``Base``,
  so reporting's Alembic autogenerate can never emit DDL for tables it doesn't
  own.
- Only the columns the report queries read are mapped.
- Types are portable (``String(36)`` for the uuid PK, not a dialect UUID) so
  the unit-test fixture can create these tables on sqlite. This mirrors the
  upstream schema exactly: session_id is a stringified uuid4, answers live in
  ``quiz_answers`` (W3-F2).
"""
import enum

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
)
from sqlalchemy.orm import declarative_base

TmsBase = declarative_base()


class SessionStatus(str, enum.Enum):
    """Mirror of test-management-service's SessionStatus enum."""

    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class TmsTest(TmsBase):
    """tests — only the columns attempt rows are labelled with."""

    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)


class TmsSession(TmsBase):
    """sessions — one row per quiz attempt (W3-F1/W3-F2).

    ``server_now`` is the server-authoritative start anchor, exposed here as
    ``started_at`` while keeping the upstream column name. ``submitted_at`` is
    set only when the session finalizes (status SUBMITTED), so
    duration = submitted_at - started_at.
    """

    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    status = Column(
        Enum(SessionStatus, name="sessionstatus", create_constraint=False),
        nullable=False,
    )
    started_at = Column("server_now", DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    question_ids = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)


class TmsAnswer(TmsBase):
    """quiz_answers — one scored row per answered question; score is a [0, 1]
    fraction (exact-match binary or Jaccard partial credit, W3-F2)."""

    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    question_id = Column(String(64), nullable=False)
    question_index = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)
