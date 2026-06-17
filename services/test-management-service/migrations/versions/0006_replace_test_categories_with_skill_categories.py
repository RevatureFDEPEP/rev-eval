"""0006_replace_test_categories_with_skill_categories

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("test_categories")
    op.create_table(
        "skill_categories",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("skill_categories")
    op.create_table(
        "test_categories",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), primary_key=True),
    )
