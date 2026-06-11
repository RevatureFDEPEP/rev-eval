"""add_sessions_table

Revision ID: a1b2c3d4e5f6
Revises: ff454e271dda
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ff454e271dda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('server_now', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'SUBMITTED', 'EXPIRED', name='sessionstatus'), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=False),
        sa.Column('question_ids', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['test_id'], ['tests.id'], ),
        sa.PrimaryKeyConstraint('session_id'),
    )
    op.create_index(op.f('ix_sessions_session_id'), 'sessions', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sessions_session_id'), table_name='sessions')
    op.drop_table('sessions')
    sa.Enum(name='sessionstatus').drop(op.get_bind(), checkfirst=True)
