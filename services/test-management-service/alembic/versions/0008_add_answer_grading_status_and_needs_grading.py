"""Answer manual-grading state + session needs_grading (W5-F1)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-17 00:00:00.000000

W5-F1: free-text answers can't be auto-scored, so they are recorded
PENDING_REVIEW and graded manually by a trainer instead of a misleading 0.0.
Adds a ``grading_status`` lifecycle (AUTO | PENDING_REVIEW | GRADED) plus the
grade payload (feedback, graded_by_id, graded_at) on ``answers``, and a
``needs_grading`` flag on ``sessions`` set when a finalized attempt still holds
ungraded free-text answers (its score is provisional until graded).

Existing rows backfill to AUTO / needs_grading=false (the historical
auto-scored state).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    grading_status = sa.Enum(
        'AUTO', 'PENDING_REVIEW', 'GRADED', name='gradingstatus'
    )
    grading_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'answers',
        sa.Column(
            'grading_status',
            grading_status,
            nullable=False,
            server_default='AUTO',
        ),
    )
    op.add_column('answers', sa.Column('feedback', sa.Text(), nullable=True))
    op.add_column('answers', sa.Column('graded_by_id', sa.Integer(), nullable=True))
    op.add_column('answers', sa.Column('graded_at', sa.DateTime(), nullable=True))

    op.add_column(
        'sessions',
        sa.Column(
            'needs_grading',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('sessions', 'needs_grading')
    op.drop_column('answers', 'graded_at')
    op.drop_column('answers', 'graded_by_id')
    op.drop_column('answers', 'feedback')
    op.drop_column('answers', 'grading_status')
    sa.Enum(name='gradingstatus').drop(op.get_bind(), checkfirst=True)
