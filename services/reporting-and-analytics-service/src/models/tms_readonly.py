"""Read-only mapped copies of test-management-service tables.

These tables live in test-management-service's Postgres (``eval_ai_dev``) and
are owned by that service's Alembic chain — this service only ever SELECTs
from them, over the dedicated ``tms_engine``/``get_tms_db`` in src/db/session.
See docs/adr/0001-reporting-cross-service-data-access.md.

Containment rules:
- Every TMS mapping lives in this module, on ``TmsBase`` — never on the
  reporting ``Base``, so reporting's Alembic autogenerate can never emit DDL
  for tables it doesn't own.
- Only the columns the report queries read are mapped; upstream columns this
  service ignores are intentionally absent.
- Column types use portable SQLAlchemy types (``sa.Uuid`` rather than the
  postgresql dialect UUID) so the unit-test fixture can create these tables
  on sqlite.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import declarative_base

TmsBase = declarative_base()


class SessionStatus(str, enum.Enum):
    """Mirror of test-management-service's SessionStatus enum."""

    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class GradingStatus(str, enum.Enum):
    """Mirror of test-management-service's GradingStatus enum (W5-F1).

    ``PENDING_REVIEW`` answers (ungraded free text) are excluded from the
    attempt score until a trainer grades them.
    """

    AUTO = "AUTO"
    PENDING_REVIEW = "PENDING_REVIEW"
    GRADED = "GRADED"


class TmsTest(TmsBase):
    """tests — only the columns attempt rows are labelled with."""

    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)


class TmsSession(TmsBase):
    """sessions — one row per quiz attempt (W3-F1/W3-F2).

    ``server_now`` is the server-authoritative start anchor; it is exposed
    here as ``started_at`` while keeping the upstream column name.
    ``submitted_at`` is set only when the session finalizes (status
    SUBMITTED), so duration = submitted_at - started_at.
    """

    __tablename__ = "sessions"

    session_id = Column(Uuid, primary_key=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    status = Column(
        Enum(SessionStatus, name="sessionstatus", create_constraint=False),
        nullable=False,
    )
    started_at = Column("server_now", DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    # True when the finalized attempt still has ungraded free-text answers
    # (W5-F1) — its score is provisional until graded. Default is for the
    # sqlite test fixture only; the live column carries a server default.
    needs_grading = Column(Boolean, nullable=False, default=False)


class TmsAnswer(TmsBase):
    """answers — one scored row per question slot; score is a [0, 1] fraction.

    ``question_id`` is the Mongo ``_id`` of the scored question — the stable
    identity for per-question difficulty grouping (``question_index`` varies
    per session because questions are randomly sampled). ``is_correct`` is
    True only for a perfect answer (W3-F2 scoring).
    """

    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(Uuid, ForeignKey("sessions.session_id"), nullable=False)
    question_id = Column(String, nullable=False)
    question_index = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    # Manual-grading lifecycle (W5-F1); PENDING_REVIEW excluded from the score.
    # Default is for the sqlite test fixture; the live column has a server default.
    grading_status = Column(
        Enum(GradingStatus, name="gradingstatus", create_constraint=False),
        nullable=False,
        default=GradingStatus.AUTO,
    )
