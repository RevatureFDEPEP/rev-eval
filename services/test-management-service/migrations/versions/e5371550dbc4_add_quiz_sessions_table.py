"""add quiz_sessions table (W3-F1)

Revision ID: e5371550dbc4
Revises: 693cff81dc38
Create Date: 2026-06-17

Adds the server-authoritative quiz_sessions table backing
``POST /v1/api/test-sessions/``. Chains on the category-domain baseline
(693cff81dc38). Batch mode keeps the create/drop portable across SQLite and
Postgres.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5371550dbc4"
down_revision: str | None = "693cff81dc38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("session_token", sa.String(length=128), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("server_now", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("quiz_sessions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_quiz_sessions_test_id"), ["test_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_quiz_sessions_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("quiz_sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quiz_sessions_user_id"))
        batch_op.drop_index(batch_op.f("ix_quiz_sessions_test_id"))

    op.drop_table("quiz_sessions")
