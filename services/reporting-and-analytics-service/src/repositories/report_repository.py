"""Read-only report queries over test-management-service's tables.

Every statement here SELECTs from the read-only TMS mappings
(src/models/tms_readonly.py) via the dedicated TMS engine — aggregation stays
in SQL (func.avg/count/sum + subqueries), never re-computed client-side.
"""
from typing import Tuple

from sqlalchemy import Select, case, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import SessionStatus, TmsAnswer, TmsSession, TmsTest
from src.schemas.report_schema import AttemptsQuery


def _session_score_subquery():
    """Per-session score: answers carry [0, 1] fractions, one row per question
    slot, so AVG x100 is the attempt's percentage score."""
    return (
        select(
            TmsAnswer.session_id.label("session_id"),
            (func.avg(TmsAnswer.score) * 100).label("score"),
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


class ReportRepository:
    @staticmethod
    async def user_summary(db: AsyncSession, user_id: int):
        """Summary aggregates + most-recent attempt in one round trip.

        One aggregate subquery (count/avg/max/sum over the user's SUBMITTED
        sessions) cross-joined with a LIMIT-1 subquery for the most recent
        row; the outer join keeps the zero-attempt aggregate row.
        """
        score_sq = _session_score_subquery()
        submitted = (
            select(
                TmsSession.session_id,
                TmsSession.submitted_at,
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
                TmsSession.submitted_at.label("recent_submitted_at"),
                recent_score_sq.c.score.label("recent_score"),
            )
            .join(TmsTest, TmsTest.id == TmsSession.test_id)
            .outerjoin(recent_score_sq, recent_score_sq.c.session_id == TmsSession.session_id)
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
        result = await db.execute(stmt)
        return result.one()

    @staticmethod
    async def user_attempts(
        db: AsyncSession, user_id: int, query: AttemptsQuery
    ) -> Tuple[list, int]:
        """Filtered, sorted, paginated attempt history + total row count."""
        score_sq = _session_score_subquery()
        # Score (and duration) are only meaningful once a session finalized;
        # an ACTIVE session's partial average would read as a final score.
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
                score_col,
            )
            .join(TmsTest, TmsTest.id == TmsSession.test_id)
            .outerjoin(score_sq, score_sq.c.session_id == TmsSession.session_id)
            .where(TmsSession.user_id == user_id)
        )
        base = ReportRepository._apply_filters(base, query)

        total = await db.scalar(
            select(func.count()).select_from(base.subquery())
        )

        sort_field, _, direction = query.sort.partition(":")
        sort_col = {
            "submitted_at": TmsSession.submitted_at,
            "created_at": TmsSession.created_at,
            "score": score_col,
        }[sort_field]
        ordering = sort_col.desc() if direction == "desc" else sort_col.asc()
        stmt = (
            base.order_by(ordering.nulls_last(), TmsSession.session_id)
            .offset((query.page - 1) * query.size)
            .limit(query.size)
        )
        result = await db.execute(stmt)
        return list(result.all()), int(total or 0)

    @staticmethod
    def _apply_filters(stmt: Select, query: AttemptsQuery) -> Select:
        if query.test_id is not None:
            stmt = stmt.where(TmsSession.test_id == query.test_id)
        if query.status is not None:
            stmt = stmt.where(TmsSession.status == query.status)
        # Date range bounds the attempt start (exists for every status);
        # `to` is inclusive of the full end date.
        if query.date_from is not None:
            stmt = stmt.where(func.date(TmsSession.started_at) >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(func.date(TmsSession.started_at) <= query.date_to)
        return stmt
