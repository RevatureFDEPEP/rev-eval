# src/models/answer.py
"""Answer ORM model (W3-F2).

One row per scored answer a candidate submits during a quiz session. The row is
the durable, server-authoritative record of *what was submitted* and *what it
scored* — the score is computed by the pure ``src.scoring`` engine from the
answer key fetched server-side, never trusted from the client.

Two unique constraints, both deliberate:

* ``uq_answers_session_idempotency (session_id, idempotency_key)`` — the
  structural backstop for idempotent replays. A client that retries the same
  ``POST .../answer`` with the same ``Idempotency-Key`` must get the *prior*
  result, scored exactly once. The route reads-then-returns the existing row,
  but the unique constraint is what closes the concurrent-double-submit race
  (two in-flight retries) that an application-level check alone cannot.

* ``uq_answers_session_question (session_id, question_id)`` — DECISION: enforce
  **one answer per question per session**. A quiz session walks its frozen
  question list once (``current_index`` advances monotonically), so a second
  answer for the same question is a protocol error, not an update. Making it a
  DB constraint means a buggy/forged client cannot silently double-score a
  question or corrupt ``current_index``. (The alternative — allowing
  overwrite/last-write-wins — was rejected: it complicates idempotency,
  scoring-once, and the submitted-state lock for no candidate-facing benefit.)

``idempotency_key`` is nullable: a client may submit without one (then there is
no dedup, which is acceptable for a non-retried call). SQLite and Postgres both
treat ``NULL`` as distinct in a unique index, so multiple key-less answers do
not collide on the idempotency constraint — only the per-question constraint
bounds them, which is the intended behavior.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from src.db.session import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now (never naive ``utcnow``)."""
    return datetime.now(UTC)


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "idempotency_key", name="uq_answers_session_idempotency"
        ),
        UniqueConstraint(
            "session_id", "question_id", name="uq_answers_session_question"
        ),
    )

    # Opaque UUID hex string PK (mirrors QuizSession.id).
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)

    # The session this answer belongs to.
    session_id = Column(
        String(32), ForeignKey("quiz_sessions.id"), nullable=False, index=True
    )

    # The question that was answered (qms Mongo _id string).
    question_id = Column(String(64), nullable=False)

    # Exactly what the candidate submitted (JSON array; order/dupes irrelevant
    # to scoring but preserved verbatim for audit/re-scoring).
    submitted_answers = Column(JSON, nullable=False, default=list)

    # Server-computed score in [0.0, 1.0] and the full-match flag.
    score = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)

    # Optional client-supplied idempotency key (Idempotency-Key header).
    idempotency_key = Column(String(128), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
