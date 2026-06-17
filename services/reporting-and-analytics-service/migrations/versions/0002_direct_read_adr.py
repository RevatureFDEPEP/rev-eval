"""0002_direct_read_adr

No new tables. Reporting service reads quiz_sessions and session_answers
directly from eval_ai_dev (test-management DB). See docs/adr/001-reporting-data-access.md.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-17

"""

from typing import Sequence, Union

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
