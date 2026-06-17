"""baseline (empty)

Empty baseline for the reporting datastore. This service reads test-management's
schema over a read-only engine and owns NO domain tables of its own (ADR 0001),
so this revision is — and is expected to remain — head. Its only job is to make
`alembic upgrade head` a valid no-op that establishes the revision chain and the
`alembic_version` table in reporting's private database, isolated from
test-management's Alembic chain in eval_ai_dev.

Revision ID: 0001
Revises:
Create Date: 2026-06-17

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Intentionally empty — reporting owns no tables (direct-read; see ADR 0001).
    pass


def downgrade() -> None:
    pass
