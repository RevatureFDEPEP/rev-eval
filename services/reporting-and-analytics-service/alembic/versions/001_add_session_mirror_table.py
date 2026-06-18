"""Add session_mirror table

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
        "session_mirror",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.String(64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "EXPIRED",
                "COMPLETED",
                "ABANDONED",
                "SUBMITTED",
                name="attemptstatus",
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "time_spent_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_session_mirror_user_id", "session_mirror", ["user_id"])
    op.create_index("ix_session_mirror_test_id", "session_mirror", ["test_id"])
    op.create_index("ix_session_mirror_created_at", "session_mirror", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_session_mirror_created_at", table_name="session_mirror")
    op.drop_index("ix_session_mirror_test_id", table_name="session_mirror")
    op.drop_index("ix_session_mirror_user_id", table_name="session_mirror")
    op.drop_table("session_mirror")
    op.execute("DROP TYPE IF EXISTS attemptstatus")
