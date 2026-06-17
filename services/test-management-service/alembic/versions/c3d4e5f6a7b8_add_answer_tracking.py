"""Add answer tracking tables and extend sessions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend sessions table
    op.add_column("sessions", sa.Column("question_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("sessions", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    # Back-fill existing rows so the column is never null going forward
    op.execute("UPDATE sessions SET question_ids = '[]'::json WHERE question_ids IS NULL")
    op.alter_column("sessions", "question_ids", nullable=False)

    # Per-question answer records
    op.create_table(
        "session_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.String(64), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("submitted_answers", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("earned_points", sa.Float(), nullable=False),
        sa.Column("max_points", sa.Float(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "question_index", name="uq_session_answer_index"),
    )
    op.create_index("ix_session_answers_session_id", "session_answers", ["session_id"])

    # Idempotency dedupe table
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_idempotency_keys_session_id", "idempotency_keys", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_session_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_session_answers_session_id", table_name="session_answers")
    op.drop_table("session_answers")
    op.drop_column("sessions", "submitted_at")
    op.drop_column("sessions", "question_ids")
