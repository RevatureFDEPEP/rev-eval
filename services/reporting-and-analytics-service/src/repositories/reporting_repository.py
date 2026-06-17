"""Read-only aggregate queries over test-management's shared tables.

All queries are SELECT-only. Time-on-task is intentionally NOT computed in SQL
(``submitted_at - started_at`` has no portable cross-dialect form); the service
layer sums it in Python from the timestamps returned here.
"""

from datetime import date, datetime

from sqlalchemy import Integer, Select, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import QuizSession, SessionAnswer, Test
from src.schemas.reporting_schema import SORTABLE_FIELDS, AttemptsQuery


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


def _apply_filters(stmt: Select, q: AttemptsQuery) -> Select:
    if q.test_id is not None:
        stmt = stmt.where(QuizSession.test_id == q.test_id)
    if q.status is not None:
        stmt = stmt.where(QuizSession.status == q.status)
    if q.date_from is not None:
        stmt = stmt.where(QuizSession.created_at >= _start_of_day(q.date_from))
    if q.date_to is not None:
        stmt = stmt.where(QuizSession.created_at < _end_of_day_exclusive(q.date_to))
    return stmt


def _start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _end_of_day_exclusive(d: date) -> datetime:
    # inclusive upper bound on the date => strictly-less-than next midnight
    from datetime import timedelta

    return _start_of_day(d) + timedelta(days=1)


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

        # total before pagination
        total = await db.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )

        # stable sort: requested field (NULLs last) then session_id tiebreak
        field = q.sort.split(":")[0]
        if field not in SORTABLE_FIELDS:
            field = "submitted_at"
        descending = q.sort.endswith(":desc")
        col = getattr(QuizSession, field)
        order = col.desc() if descending else col.asc()
        stmt = (
            base.order_by(order.nullslast(), QuizSession.session_id.asc())
            .limit(q.size)
            .offset((q.page - 1) * q.size)
        )
        rows = (await db.execute(stmt)).all()
        return list(rows), int(total or 0)

    @staticmethod
    async def fetch_score_aggregates(db: AsyncSession, user_id: int):
        """Single SQL aggregate: total attempts, average + best per-session score.

        ``average``/``best`` are over a per-session score subquery
        (SUM(points_earned)/SUM(max_points)); func.avg/func.max skip the NULL
        scores of answerless sessions, while func.count(distinct) still counts
        every attempt.
        """
        answers = _answers_aggregate()
        score = (answers.c.points_sum / func.nullif(answers.c.max_sum, 0)).label(
            "score"
        )
        per_session = (
            select(QuizSession.session_id.label("session_id"), score)
            .select_from(QuizSession)
            .outerjoin(answers, answers.c.session_id == QuizSession.session_id)
            .where(QuizSession.user_id == user_id)
            .subquery()
        )
        stmt = select(
            func.count(func.distinct(per_session.c.session_id)).label("total_attempts"),
            func.avg(per_session.c.score).label("average_score"),
            func.max(per_session.c.score).label("best_score"),
        )
        return (await db.execute(stmt)).one()

    @staticmethod
    async def fetch_session_durations(db: AsyncSession, user_id: int) -> list:
        """(started_at, submitted_at) for the user's submitted sessions."""
        stmt = select(QuizSession.started_at, QuizSession.submitted_at).where(
            QuizSession.user_id == user_id,
            QuizSession.submitted_at.is_not(None),
            QuizSession.started_at.is_not(None),
        )
        return (await db.execute(stmt)).all()

    @staticmethod
    async def fetch_most_recent_attempt(db: AsyncSession, user_id: int):
        """The single latest attempt by created_at (subquery for the summary)."""
        answers = _answers_aggregate()
        stmt = (
            select(*_attempt_columns(answers), QuizSession.created_at)
            .select_from(QuizSession)
            .outerjoin(Test, Test.id == QuizSession.test_id)
            .outerjoin(answers, answers.c.session_id == QuizSession.session_id)
            .where(QuizSession.user_id == user_id)
            .order_by(QuizSession.created_at.desc().nullslast())
            .limit(1)
        )
        return (await db.execute(stmt)).first()

    @staticmethod
    async def user_has_any_session(db: AsyncSession, user_id: int) -> bool:
        stmt = select(cast(func.count(), Integer)).where(QuizSession.user_id == user_id)
        return bool(await db.scalar(stmt))
