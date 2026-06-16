"""add sessions.draft_answers autosave column

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-16 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Advisory autosave snapshot of in-progress answers (W3-F4). Nullable: NULL
    # until the candidate's first autosave; never scored, never advances state.
    op.add_column('sessions', sa.Column('draft_answers', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'draft_answers')
