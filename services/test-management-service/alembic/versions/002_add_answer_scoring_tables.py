"""Add answer scoring tables and session columns

Revision ID: 002
Revises: 001
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add columns to sessions ──────────────────────────────────────────────
    op.add_column("sessions", sa.Column("question_ids", sa.JSON(), nullable=True))
    op.add_column("sessions", sa.Column("submitted_at", sa.DateTime(), nullable=True))

    # Add SUBMITTED to the sessionstatus enum (PostgreSQL-specific; SQLite ignores)
    # Wrapped in a try/except so SQLite-based test runs don't fail
    try:
        op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'SUBMITTED'")
    except Exception:
        pass

    # ── session_answers table ────────────────────────────────────────────────
    op.create_table(
        "session_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_id", sa.String(128), nullable=False),
        sa.Column("submitted_answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("answered_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_session_answers_session_id", "session_answers", ["session_id"])

    # ── idempotency_keys table ────────────────────────────────────────────────
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", "session_id", name="uq_idempotency_session"),
    )
    op.create_index("ix_idempotency_keys_session_id", "idempotency_keys", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_session_id", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_session_answers_session_id", table_name="session_answers")
    op.drop_table("session_answers")
    op.drop_column("sessions", "submitted_at")
    op.drop_column("sessions", "question_ids")
