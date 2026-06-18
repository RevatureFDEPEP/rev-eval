"""add submitted_at to quiz_sessions (W3-F2)

Revision ID: b2d4f6a8c0e1
Revises: 7a3298917a91
Create Date: 2026-06-18

Adds a nullable, timezone-aware ``submitted_at`` column to ``quiz_sessions``.
The column is server-stamped once, on the transition to ``submitted`` (the
candidate answered the final question); it stays NULL while in_progress and on
the ``expired`` transition. W4-F1 reporting reads it for "most recent attempt"
and sort-by-submitted_at.

Nullable with no server_default: existing rows (and every row that never
reaches ``submitted``) keep a NULL submitted_at, which is the intended sentinel.
Batch mode keeps the add/drop portable across SQLite and Postgres.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d4f6a8c0e1"
down_revision: str | None = "7a3298917a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("quiz_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("quiz_sessions", schema=None) as batch_op:
        batch_op.drop_column("submitted_at")
