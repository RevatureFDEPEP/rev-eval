"""require idempotency_key on session_answers

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-11

The answer-submit route requires an Idempotency-Key header, but the column was
nullable — a future non-FastAPI write path could insert a NULL key and slip past
the (session_id, idempotency_key) dedup constraint (NULLs are distinct in a
unique index). Making the column NOT NULL closes that gap at the DB level.

Any pre-existing NULL keys are backfilled with a synthetic, row-unique value so
the constraint cannot collide on legacy rows.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill legacy NULL keys with a deterministic, row-unique value.
    op.execute(
        "UPDATE session_answers "
        "SET idempotency_key = 'legacy-' || id "
        "WHERE idempotency_key IS NULL"
    )
    op.alter_column(
        "session_answers",
        "idempotency_key",
        existing_type=sa.String(length=64),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "session_answers",
        "idempotency_key",
        existing_type=sa.String(length=64),
        nullable=True,
    )
