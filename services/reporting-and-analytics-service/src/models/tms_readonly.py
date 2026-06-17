"""Read-only ORM mappings over test-management-service's tables.

This service does NOT own these tables — test-management-service does. We map
only the columns reporting reads, on the shared ``Base``, purely to build SELECT
queries. ``create_all`` is never called here (see adr/0001), so these
mappings never create or migrate anything; they only describe what already
exists in the shared ``eval_ai_dev`` database.

The cross-schema ``--integration`` test seeds through test-management's own
Alembic-migrated tables and asserts these queries still resolve, so any drift
between this mirror and the real schema fails CI.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, Integer, String

from src.db.session import Base


class QuizSessionStatus(enum.StrEnum):
    """Mirror of test-management's session status enum (PG type ``quizsessionstatus``)."""

    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    session_id = Column(String(36), primary_key=True)
    test_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    # Mapped with the same enum + PG type name so filters bind correctly on
    # Postgres (status = 'SUBMITTED'::quizsessionstatus) and string-compare on
    # SQLite. create_type is irrelevant — we never create_all.
    status = Column(Enum(QuizSessionStatus, name="quizsessionstatus"), nullable=False)
    created_at = Column(DateTime)
    started_at = Column(DateTime)
    submitted_at = Column(DateTime)


class SessionAnswer(Base):
    __tablename__ = "session_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    is_correct = Column(Boolean, nullable=False)
    points_earned = Column(Float, nullable=False)
    max_points = Column(Float, nullable=False)
