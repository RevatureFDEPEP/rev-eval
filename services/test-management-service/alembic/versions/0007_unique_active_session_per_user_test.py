"""One ACTIVE session per (user_id, test_id) — partial unique index

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-10 00:00:00.000000

W3-F7 item 3: POST /sessions reuses an existing ACTIVE session instead of
minting duplicates; this index is the race backstop for the lookup-then-insert
window. Existing duplicate ACTIVE rows (possible on dev databases) are
resolved first: the newest row per (user_id, test_id) stays ACTIVE, older
ones flip to EXPIRED.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Dedupe existing ACTIVE rows, then add the partial unique index."""
    op.execute(
        """
        UPDATE sessions SET status = 'EXPIRED'
        WHERE status = 'ACTIVE'
          AND session_id NOT IN (
            SELECT DISTINCT ON (user_id, test_id) session_id
            FROM sessions
            WHERE status = 'ACTIVE'
            ORDER BY user_id, test_id, created_at DESC NULLS LAST
          )
        """
    )
    op.create_index(
        'uq_sessions_active_user_test',
        'sessions',
        ['user_id', 'test_id'],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    """Downgrade schema (expired duplicates are not restored)."""
    op.drop_index('uq_sessions_active_user_test', table_name='sessions')
