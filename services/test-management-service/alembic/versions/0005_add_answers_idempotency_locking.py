"""Add answers + idempotency_keys, sessions.submitted_at

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09 21:03:41.304198

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (W3-F2): scored answers, idempotency dedup, submitted_at."""
    op.create_table('answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('question_id', sa.String(), nullable=False),
    sa.Column('question_index', sa.Integer(), nullable=False),
    sa.Column('submitted_answers', sa.JSON(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'question_index', name='uq_answer_session_index')
    )
    op.create_index(op.f('ix_answers_id'), 'answers', ['id'], unique=False)
    op.create_table('idempotency_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('response_body', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'idempotency_key', name='uq_idempotency_session_key')
    )
    op.create_index(op.f('ix_idempotency_keys_id'), 'idempotency_keys', ['id'], unique=False)
    op.add_column('sessions', sa.Column('submitted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sessions', 'submitted_at')
    op.drop_index(op.f('ix_idempotency_keys_id'), table_name='idempotency_keys')
    op.drop_table('idempotency_keys')
    op.drop_index(op.f('ix_answers_id'), table_name='answers')
    op.drop_table('answers')
