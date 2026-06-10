"""add session_answers table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-09

Adds the session_answers table that stores each scored answer submitted during
a quiz session. The idempotency_key unique constraint (per session) prevents
double-scoring on retried requests.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("submitted_answers", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("points_earned", sa.Float(), nullable=False),
        sa.Column("max_points", sa.Float(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["quiz_sessions.session_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "idempotency_key",
            name="uq_session_answer_idempotency",
        ),
    )
    op.create_index(
        op.f("ix_session_answers_session_id"),
        "session_answers",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_answers_idempotency_key"),
        "session_answers",
        ["idempotency_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_session_answers_idempotency_key"), table_name="session_answers"
    )
    op.drop_index(op.f("ix_session_answers_session_id"), table_name="session_answers")
    op.drop_table("session_answers")
