"""Reporting performance indexes

Revision ID: 0001
Revises:
Create Date: 2026-06-15

Adds composite indexes on quiz_sessions to speed up aggregate and ranking
queries issued by the reporting service.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qs_test_status_score "
        "ON quiz_sessions (test_id, status, percentage_score)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qs_test_user "
        "ON quiz_sessions (test_id, user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_qs_test_status_score")
    op.execute("DROP INDEX IF EXISTS ix_qs_test_user")
