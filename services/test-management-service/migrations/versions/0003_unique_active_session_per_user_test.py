"""add partial unique index: one ACTIVE session per (test_id, user_id)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09

Moves the "at most one ACTIVE session per participant+test" invariant from
application code into the database. PostgreSQL supports partial (WHERE-clause)
unique indexes natively; SQLite (used in tests) does not, so the index is
created only when the dialect supports it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_quiz_sessions_active_user_test"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            INDEX_NAME,
            "quiz_sessions",
            ["test_id", "user_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(INDEX_NAME, table_name="quiz_sessions")
