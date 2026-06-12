"""Scoring engine columns — idempotency, per-part scores, EXPIRED status, nullable token_hash

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make token_hash nullable — scoring engine route does not issue tokens
    op.alter_column("quiz_sessions", "token_hash", nullable=True)

    # Per-part scores (scoring engine stores A and B scores separately)
    op.add_column("quiz_sessions", sa.Column("part_a_score", sa.Float(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("part_b_score", sa.Float(), nullable=True))

    # Idempotency columns — store SHA-256 hash of Idempotency-Key header
    op.add_column("quiz_sessions", sa.Column("part_a_idempotency_hash", sa.String(64), nullable=True))
    op.add_column("quiz_sessions", sa.Column("part_b_idempotency_hash", sa.String(64), nullable=True))
    op.add_column("quiz_sessions", sa.Column("part_a_response_cache", sa.JSON(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("part_b_response_cache", sa.JSON(), nullable=True))

    # Add EXPIRED to the sessionstatus enum (Postgres requires explicit ALTER TYPE)
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'EXPIRED'")


def downgrade() -> None:
    op.drop_column("quiz_sessions", "part_b_response_cache")
    op.drop_column("quiz_sessions", "part_a_response_cache")
    op.drop_column("quiz_sessions", "part_b_idempotency_hash")
    op.drop_column("quiz_sessions", "part_a_idempotency_hash")
    op.drop_column("quiz_sessions", "part_b_score")
    op.drop_column("quiz_sessions", "part_a_score")
    op.alter_column("quiz_sessions", "token_hash", nullable=False)
    # Note: removing an enum value in Postgres requires recreating the type;
    # downgrade leaves EXPIRED in the enum to avoid that complexity.
