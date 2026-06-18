"""Initial baseline — no tables created (service reads existing tables)

Revision ID: a1b2c3d4
Revises:
Create Date: 2026-06-17 00:00:00.000000

This service reads the sessions and session_answers tables owned by
test-management-service. No new tables are created in this migration.
This revision is a baseline marker. Future migrations may add a local
reporting_events or reporting_cache table if a sync strategy is adopted.
"""
from typing import Sequence, Union

revision: str = "a1b2c3d4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass  # No tables created — service reads existing tables


def downgrade() -> None:
    pass
