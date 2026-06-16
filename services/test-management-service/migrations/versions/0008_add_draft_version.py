"""add draft_version to quiz_sessions

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-13

W3-F4 monotonic draft guard: a strictly increasing version stamped by the client
on each autosave. The server only overwrites draft_answers when the incoming
version exceeds the stored one, so a late-arriving stale snapshot can't clobber a
fresher one under out-of-order delivery. NOT NULL, defaults to 0 (no draft yet);
existing rows are backfilled to 0 by the server_default.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quiz_sessions",
        sa.Column(
            "draft_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("quiz_sessions", "draft_version")
