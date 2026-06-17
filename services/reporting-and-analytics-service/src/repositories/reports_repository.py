# src/repositories/reports_repository.py
"""Read-only report queries over test-management-service's tables.

Every statement SELECTs from the read-only TMS mappings (tms_readonly.py) via
the dedicated TMS engine. Aggregation stays in SQL (func.avg/count/sum +
subqueries), never re-computed client-side.

Score convention: ``quiz_answers.score`` is a [0, 1] fraction, one row per
answered question, so a session's score is ``AVG(score) * 100`` (a percentage).
"""
from sqlalchemy import Select, asc, case, desc, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import SessionStatus, TmsAnswer, TmsSession, TmsTest
from src.schemas.reports_schema import SORT_FIELDS, AttemptsQuery


def _session_score_subquery():
    """Per-session aggregates: percentage score + count of answered questions."""
    return (
        select(
            TmsAnswer.session_id.label("session_id"),
            (func.avg(TmsAnswer.score) * 100).label("score"),
            func.count(TmsAnswer.id).label("answered"),
        )
        .group_by(TmsAnswer.session_id)
        .subquery()
    )


def _duration_seconds(db: AsyncSession):
    """submitted_at - started_at in seconds (NULL until a session finalizes).

    Postgres subtracts timestamps to an interval (EXTRACT EPOCH); the sqlite
    unit-test fixture needs julianday arithmetic instead.
    """
    if db.bind.dialect.name == "sqlite":
        return (
            func.julianday(TmsSession.submitted_at) - func.julianday(TmsSession.started_at)
        ) * 86400
    return func.extract("epoch", TmsSession.submitted_at - TmsSession.started_at)


async def user_summary(db: AsyncSession, user_id: int):
    """Summary aggregates + most-recent attempt in ONE round trip.

    An aggregate subquery (count/avg/max/sum over the user's SUBMITTED sessions)
    is cross-joined with a LIMIT-1 subquery for the most recent row; the outer
    join keeps the zero-attempt aggregate row (all NULL / 0).
    """
    score_sq = _session_score_subquery()
    submitted = (
        select(
            TmsSession.session_id,
            score_sq.c.score,
            _duration_seconds(db).label("duration_seconds"),
        )
        .outerjoin(score_sq, score_sq.c.session_id == TmsSession.session_id)
        .where(
            TmsSession.user_id == user_id,
            TmsSession.status == SessionStatus.SUBMITTED,
        )
        .subquery()
    )
    aggregates = select(
        func.count(submitted.c.session_id).label("total_attempts"),
        func.avg(submitted.c.score).label("avg_score"),
        func.max(submitted.c.score).label("best_score"),
        func.sum(submitted.c.duration_seconds).label("total_time_seconds"),
    ).subquery()

    recent_score_sq = _session_score_subquery()
    most_recent = (
        select(
            TmsSession.session_id.label("recent_session_id"),
            TmsSession.test_id.label("recent_test_id"),
            TmsTest.name.label("recent_test_name"),
            TmsSession.status.label("recent_status"),
            TmsSession.submitted_at.label("recent_submitted_at"),
            recent_score_sq.c.score.label("recent_score"),
        )
        .outerjoin(TmsTest, TmsTest.id == TmsSession.test_id)
        .outerjoin(
            recent_score_sq, recent_score_sq.c.session_id == TmsSession.session_id
        )
        .where(
            TmsSession.user_id == user_id,
            TmsSession.status == SessionStatus.SUBMITTED,
        )
        .order_by(TmsSession.submitted_at.desc())
        .limit(1)
        .subquery()
    )

    stmt = select(aggregates, most_recent).select_from(
        aggregates.join(most_recent, true(), isouter=True)
    )
    return (await db.execute(stmt)).one()


async def user_attempts(db: AsyncSession, user_id: int, q: AttemptsQuery):
    """Filtered, sorted, paginated attempt history + total row count.

    Returns ``(rows, total)``. Each row carries the session, its test name,
    duration, answered-count, and a score that is NULL unless the session is
    SUBMITTED (an ACTIVE session's running average is not a final score).
    """
    score_sq = _session_score_subquery()
    score_col = case(
        (TmsSession.status == SessionStatus.SUBMITTED, score_sq.c.score),
        else_=None,
    ).label("score")

    base: Select = (
        select(
            TmsSession.session_id,
            TmsSession.test_id,
            TmsTest.name.label("test_name"),
            TmsSession.status,
            TmsSession.started_at,
            TmsSession.submitted_at,
            _duration_seconds(db).label("duration_seconds"),
            func.coalesce(score_sq.c.answered, 0).label("answered"),
            score_col,
        )
        .outerjoin(TmsTest, TmsTest.id == TmsSession.test_id)
        .outerjoin(score_sq, score_sq.c.session_id == TmsSession.session_id)
        .where(TmsSession.user_id == user_id)
    )

    if q.test_id is not None:
        base = base.where(TmsSession.test_id == q.test_id)
    if q.status is not None:
        base = base.where(TmsSession.status == q.status)
    # Date range bounds the attempt START time (server_now) — present for every
    # status — so an ACTIVE attempt is not silently dropped by the filter.
    if q.date_from is not None:
        base = base.where(func.date(TmsSession.started_at) >= q.date_from)
    if q.date_to is not None:
        base = base.where(func.date(TmsSession.started_at) <= q.date_to)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    field, _, direction = q.sort.partition(":")
    if field not in SORT_FIELDS:
        field = "submitted_at"
    # Sort by the SAME CASE-adjusted score the row displays, so an ACTIVE
    # attempt (score hidden as NULL) sorts as NULL too rather than by its
    # running partial average.
    sort_col = score_col if field == "score" else getattr(TmsSession, field)
    ordering = asc(sort_col) if direction == "asc" else desc(sort_col)
    # NULLS LAST so in-progress attempts (NULL submitted_at / score) sort behind
    # completed ones rather than floating to the top of the history.
    base = base.order_by(ordering.nullslast())

    base = base.offset((q.page - 1) * q.size).limit(q.size)
    rows = (await db.execute(base)).all()
    return rows, total
