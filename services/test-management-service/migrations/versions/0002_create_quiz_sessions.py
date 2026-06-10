"""create quiz_sessions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08

First real migration: adds the quiz_sessions table backing W3-F1 quiz session
creation. Standalone (keyed by test_id + user_id), independent of
test_submissions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_sessions",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "SUBMITTED", "EXPIRED", name="quizsessionstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_quiz_sessions_session_id", "quiz_sessions", ["session_id"])
    op.create_index("ix_quiz_sessions_test_id", "quiz_sessions", ["test_id"])
    op.create_index("ix_quiz_sessions_user_id", "quiz_sessions", ["user_id"])
    op.create_index(
        "ix_quiz_sessions_session_token",
        "quiz_sessions",
        ["session_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_quiz_sessions_session_token", table_name="quiz_sessions")
    op.drop_index("ix_quiz_sessions_user_id", table_name="quiz_sessions")
    op.drop_index("ix_quiz_sessions_test_id", table_name="quiz_sessions")
    op.drop_index("ix_quiz_sessions_session_id", table_name="quiz_sessions")
    op.drop_table("quiz_sessions")
    sa.Enum(name="quizsessionstatus").drop(op.get_bind(), checkfirst=True)
