"""0004_add_quiz_sessions

Revision ID: 0004
Revises:
Create Date: 2026-06-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_token", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("test_submissions.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("STARTED", "IN_PROGRESS", "SUBMITTED", "EXPIRED", name="sessionstatus"),
            nullable=False,
            server_default="STARTED",
        ),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question_ids", sa.JSON(), nullable=False),
        sa.Column("server_now", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_quiz_sessions_session_token", "quiz_sessions", ["session_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_quiz_sessions_session_token", table_name="quiz_sessions")
    op.drop_table("quiz_sessions")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
