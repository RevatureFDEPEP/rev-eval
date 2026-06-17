"""0005_add_categories

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "test_categories",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("test_categories")
    op.drop_table("categories")
