"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-06-10

Covers: skills, tests, test_skills, test_submissions, quiz_sessions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "test_type",
            sa.Enum("QUIZ", "INTERVIEW", name="testtype"),
            nullable=False,
            server_default="QUIZ",
        ),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("curriculum", sa.String(255), nullable=True),
        sa.Column("duration", sa.Interval(), nullable=True),
        sa.Column("number_of_questions", sa.Integer(), nullable=True, server_default="20"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "test_skills",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.UniqueConstraint("test_id", "skill_id", name="uq_test_skill"),
    )

    op.create_table(
        "test_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "ASSIGNED", "IN_PROGRESS", "COMPLETED", "EVALUATED", "GRADED", "ABANDONED",
                name="submissionstatus",
            ),
            server_default="ASSIGNED",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("ai_score", sa.Integer(), nullable=True),
        sa.Column("trainer_score", sa.Integer(), nullable=True),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("test_submissions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "status",
            sa.Enum(
                "STARTED", "PART_A_IN_PROGRESS", "PART_A_COMPLETED",
                "PART_B_IN_PROGRESS", "PART_B_COMPLETED", "GRADED", "COMPLETED", "ABANDONED",
                name="sessionstatus",
            ),
            nullable=False,
            server_default="STARTED",
        ),
        sa.Column("server_now", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_questions", sa.Integer(), server_default="20"),
        sa.Column("part_a_config", sa.JSON(), nullable=True),
        sa.Column("part_b_config", sa.JSON(), nullable=True),
        sa.Column("part_a", sa.JSON(), nullable=True),
        sa.Column("part_b", sa.JSON(), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("percentage_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("quiz_sessions")
    op.drop_table("test_submissions")
    op.drop_table("test_skills")
    op.drop_table("tests")
    op.drop_table("skills")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS submissionstatus")
    op.execute("DROP TYPE IF EXISTS testtype")
