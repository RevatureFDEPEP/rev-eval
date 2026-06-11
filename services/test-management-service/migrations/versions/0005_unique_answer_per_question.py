"""unique answer per question per session

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-10

Adds a unique constraint on (session_id, question_index) so a question can be
scored at most once per session. This is the durable backstop against
double-scoring when no Idempotency-Key is supplied or a row lock is unavailable.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_session_answer_question_index",
        "session_answers",
        ["session_id", "question_index"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_session_answer_question_index", "session_answers", type_="unique"
    )
