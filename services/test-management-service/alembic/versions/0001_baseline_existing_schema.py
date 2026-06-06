"""baseline existing schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05 20:32:38.156708

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Baseline of the schema that predates Alembic (previously created by
    Base.metadata.create_all on startup): skills, tests, test_skills,
    test_submissions. The shared database also holds tables owned by
    user-service (e.g. users) — those are intentionally absent here.
    Reviewed/adjusted after autogenerate: the new categories tables were
    moved to revision 0002.
    """
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_id'), 'skills', ['id'], unique=False)
    op.create_table('tests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('test_type', sa.Enum('QUIZ', 'INTERVIEW', name='testtype'), nullable=False),
    sa.Column('role', sa.String(length=100), nullable=True),
    sa.Column('curriculum', sa.String(length=255), nullable=True),
    sa.Column('duration', sa.Interval(), nullable=True),
    sa.Column('number_of_questions', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tests_id'), 'tests', ['id'], unique=False)
    op.create_table('test_skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ),
    sa.ForeignKeyConstraint(['test_id'], ['tests.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('test_id', 'skill_id', name='uq_test_skill')
    )
    op.create_index(op.f('ix_test_skills_id'), 'test_skills', ['id'], unique=False)
    op.create_table('test_submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('assigned_by_id', sa.Integer(), nullable=True),
    sa.Column('assigned_at', sa.DateTime(), nullable=True),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.Enum('ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'EVALUATED',
                                'GRADED', 'ABANDONED', name='submissionstatus'), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('ai_score', sa.Integer(), nullable=True),
    sa.Column('trainer_score', sa.Integer(), nullable=True),
    sa.Column('final_score', sa.Integer(), nullable=True),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['test_id'], ['tests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_submissions_id'), 'test_submissions', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_test_submissions_id'), table_name='test_submissions')
    op.drop_table('test_submissions')
    op.drop_index(op.f('ix_test_skills_id'), table_name='test_skills')
    op.drop_table('test_skills')
    op.drop_index(op.f('ix_tests_id'), table_name='tests')
    op.drop_table('tests')
    op.drop_index(op.f('ix_skills_id'), table_name='skills')
    op.drop_table('skills')
    # Enum types created by the tables above
    sa.Enum(name='testtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='submissionstatus').drop(op.get_bind(), checkfirst=True)
