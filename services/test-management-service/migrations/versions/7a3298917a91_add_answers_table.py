"""add answers table (W3-F2)

Revision ID: 7a3298917a91
Revises: e5371550dbc4
Create Date: 2026-06-17

Adds the ``answers`` table backing ``POST /v1/api/test-sessions/{id}/answer``.
Chains on the quiz_sessions table (e5371550dbc4). Two unique constraints:

* ``uq_answers_session_idempotency (session_id, idempotency_key)`` — idempotent
  replay backstop (same Idempotency-Key on a session -> one scored row).
* ``uq_answers_session_question (session_id, question_id)`` — one answer per
  question per session (the session walks its frozen question list once).

Batch mode keeps the create/drop portable across SQLite and Postgres.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a3298917a91"
down_revision: str | None = "e5371550dbc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answers",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=32), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column("submitted_answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["quiz_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "idempotency_key", name="uq_answers_session_idempotency"
        ),
        sa.UniqueConstraint(
            "session_id", "question_id", name="uq_answers_session_question"
        ),
    )
    with op.batch_alter_table("answers", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_answers_session_id"), ["session_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("answers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_answers_session_id"))

    op.drop_table("answers")
