"""add session_answers and idempotency_keys tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_answers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("quiz_sessions.id"), nullable=False),
        sa.Column("question_id", sa.String(64), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False),
        sa.Column("submitted_answers", sa.JSON(), nullable=False),
        sa.Column("correct_answers", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_session_answers_id", "session_answers", ["id"])
    op.create_index("ix_session_answers_session_id", "session_answers", ["session_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(128), nullable=False, unique=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("quiz_sessions.id"), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_idempotency_keys_id", "idempotency_keys", ["id"])
    op.create_index("ix_idempotency_keys_key", "idempotency_keys", ["key"], unique=True)
    op.create_index("ix_idempotency_keys_session_id", "idempotency_keys", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_session_id", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_key", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index("ix_session_answers_session_id", table_name="session_answers")
    op.drop_index("ix_session_answers_id", table_name="session_answers")
    op.drop_table("session_answers")
