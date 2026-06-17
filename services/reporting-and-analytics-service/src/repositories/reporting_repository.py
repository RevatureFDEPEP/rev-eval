"""Read-only aggregate queries over test-management's shared tables.

All queries are SELECT-only. Time-on-task is intentionally NOT computed in SQL
(``submitted_at - started_at`` has no portable cross-dialect form); the service
layer derives it in Python from the timestamps returned here.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import QuizSession, SessionAnswer, Test
from src.schemas.reporting_schema import AttemptsQuery


def _answers_aggregate():
    """Per-session rollup of session_answers (grouped subquery)."""
    return (
        select(
            SessionAnswer.session_id.label("session_id"),
            func.count().label("total_answered"),
            func.sum(case((SessionAnswer.is_correct.is_(True), 1), else_=0)).label(
                "correct_count"
            ),
            func.sum(SessionAnswer.points_earned).label("points_sum"),
            func.sum(SessionAnswer.max_points).label("max_sum"),
        )
        .group_by(SessionAnswer.session_id)
        .subquery()
    )


def _attempt_columns(answers):
    """Columns selected for an attempt row, joining sessions → tests → answers."""
    return (
        QuizSession.session_id,
        QuizSession.test_id,
        Test.name.label("test_name"),
        QuizSession.status,
        QuizSession.started_at,
        QuizSession.submitted_at,
        func.coalesce(answers.c.total_answered, 0).label("total_answered"),
        func.coalesce(answers.c.correct_count, 0).label("correct_count"),
        answers.c.points_sum,
        answers.c.max_sum,
    )


def _start_of_day(d: date) -> datetime:
    # Naive UTC midnight — matches how test-management stores timestamps
    # (datetime.utcnow(), tz-naive). Date-range bounds are therefore UTC days.
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _apply_filters(stmt: Select, q: AttemptsQuery) -> Select:
    """Apply the attempt-history filters. The date range is on ``created_at``
    (when the attempt was made — always present, unlike submitted_at) and is
    interpreted in UTC; ``to`` is inclusive of the whole day."""
    if q.test_id is not None:
        stmt = stmt.where(QuizSession.test_id == q.test_id)
    if q.status is not None:
        stmt = stmt.where(QuizSession.status == q.status)
    if q.date_from is not None:
        stmt = stmt.where(QuizSession.created_at >= _start_of_day(q.date_from))
    if q.date_to is not None:
        stmt = stmt.where(
            QuizSession.created_at < _start_of_day(q.date_to) + timedelta(days=1)
        )
    return stmt


class ReportingRepository:
    @staticmethod
    async def fetch_attempts(
        db: AsyncSession, user_id: int, q: AttemptsQuery
    ) -> tuple[list, int]:
        """Return (rows, total) for a user's attempt history, filtered + paged."""
        answers = _answers_aggregate()
        base = (
            select(*_attempt_columns(answers))
            .select_from(QuizSession)
            .outerjoin(Test, Test.id == QuizSession.test_id)
            .outerjoin(answers, answers.c.session_id == QuizSession.session_id)
            .where(QuizSession.user_id == user_id)
        )
        base = _apply_filters(base, q)

        # Count only the matching quiz_sessions rows — the answers rollup and the
        # tests join don't change the row count, so they're left out of COUNT.
        count_stmt = _apply_filters(
            select(func.count())
            .select_from(QuizSession)
            .where(QuizSession.user_id == user_id),
            q,
        )
        total = await db.scalar(count_stmt)

        col = getattr(QuizSession, q.sort_field)
        order = col.desc() if q.sort_descending else col.asc()
        stmt = (
            base.order_by(order.nullslast(), QuizSession.session_id.asc())
            .limit(q.size)
            .offset((q.page - 1) * q.size)
        )
        rows = (await db.execute(stmt)).all()
        return list(rows), int(total or 0)

    @staticmethod
    async def fetch_user_session_rollup(db: AsyncSession, user_id: int) -> list:
        """One query: every session for the user with its answers rollup +
        created_at. The summary's aggregates (count, avg/best score, total time,
        most-recent) are derived from these rows in the service, so the score
        formula and the 'which sessions count' rule live in exactly one place.
        """
        answers = _answers_aggregate()
        stmt = (
            select(*_attempt_columns(answers), QuizSession.created_at)
            .select_from(QuizSession)
            .outerjoin(Test, Test.id == QuizSession.test_id)
            .outerjoin(answers, answers.c.session_id == QuizSession.session_id)
            .where(QuizSession.user_id == user_id)
        )
        return (await db.execute(stmt)).all()
