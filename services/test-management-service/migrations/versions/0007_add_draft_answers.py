"""add draft_answers to quiz_sessions

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-12

W3-F4 autosave: an advisory snapshot of the participant's in-progress selections
(question_id -> option_ids). Nullable, last-write-wins, never scored, and does
not advance current_index or change status. Read back on resume so a crash/close
mid-question doesn't lose the current selection.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quiz_sessions",
        sa.Column("draft_answers", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_sessions", "draft_answers")
