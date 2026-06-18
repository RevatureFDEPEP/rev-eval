"""Add sessions table

Revision ID: 001
Revises:
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        # String(36) mirrors the SQLAlchemy model so create_all and Alembic produce identical schema.
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(128), nullable=False, unique=True),
        sa.Column("server_now", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "EXPIRED", "COMPLETED", "ABANDONED", name="sessionstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_sessions_test_id", "sessions", ["test_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_test_id", table_name="sessions")
    op.drop_table("sessions")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
