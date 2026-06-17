"""Add sessions table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type only if it doesn't already exist (init_db may have created it via create_all)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sessionstatus AS ENUM ('ACTIVE', 'COMPLETED', 'EXPIRED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.create_table(
        "sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("server_now", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "COMPLETED", "EXPIRED", name="sessionstatus", create_type=False),
            nullable=False,
            server_default="'ACTIVE'",
        ),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("session_token"),
    )
    op.create_index("ix_sessions_test_id", "sessions", ["test_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_test_id", table_name="sessions")
    op.drop_table("sessions")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
