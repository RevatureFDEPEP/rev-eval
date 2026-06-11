"""add quiz_answers table and sessions.submitted_at

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('submitted_at', sa.DateTime(), nullable=True))

    op.create_table(
        'quiz_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('question_id', sa.String(length=64), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('submitted_answers', sa.JSON(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('algorithm', sa.String(length=32), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('response_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_quiz_answers_id'), 'quiz_answers', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_session_id'), 'quiz_answers', ['session_id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_idempotency_key'), 'quiz_answers', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_quiz_answers_idempotency_key'), table_name='quiz_answers')
    op.drop_index(op.f('ix_quiz_answers_session_id'), table_name='quiz_answers')
    op.drop_index(op.f('ix_quiz_answers_id'), table_name='quiz_answers')
    op.drop_table('quiz_answers')
    op.drop_column('sessions', 'submitted_at')
