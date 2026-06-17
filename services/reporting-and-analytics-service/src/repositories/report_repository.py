"""Read-only report queries over test-management-service's tables.

Every statement here SELECTs from the read-only TMS mappings
(src/models/tms_readonly.py) via the dedicated TMS engine — aggregation stays
in SQL (func.avg/count/sum + subqueries), never re-computed client-side.
"""
from typing import Tuple

from sqlalchemy import Select, and_, case, distinct, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import (
    GradingStatus,
    SessionStatus,
    TmsAnswer,
    TmsSession,
    TmsTest,
)
from src.schemas.report_schema import AggregateQuery, AttemptsQuery


def _session_score_subquery():
    """Per-session score: answers carry [0, 1] fractions, one row per question
    slot, so AVG x100 is the attempt's percentage score.

    Ungraded free-text answers (``PENDING_REVIEW``, W5-F1) are excluded via a
    CASE→NULL that AVG skips, so a pending answer doesn't drag the score to 0;
    the attempt reads provisionally until a trainer grades it (NULL when every
    answer is still pending). Portable across Postgres + the sqlite test
    fixture (avoids a FILTER clause)."""
    scorable = case(
        (TmsAnswer.grading_status != GradingStatus.PENDING_REVIEW, TmsAnswer.score),
        else_=None,
    )
    return (
        select(
            TmsAnswer.session_id.label("session_id"),
            (func.avg(scorable) * 100).label("score"),
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


def _median_duration_parts(db: AsyncSession, sessions):
    """Median session duration per test over the ``sessions`` subquery.

    Postgres: ``percentile_cont(0.5) WITHIN GROUP`` — the spec's ordered-set
    aggregate, computed inline in the GROUP BY statement. The sqlite unit-test
    fixture can't parse WITHIN GROUP, so it falls back to the classic
    ROW_NUMBER/COUNT portable median in a joined subquery (same dialect-branch
    precedent as ``_duration_seconds``); the live compose smoke exercises the
    real percentile_cont path. Returns (join subquery or None, aggregate column).
    """
    if db.bind.dialect.name != "sqlite":
        return None, func.percentile_cont(0.5).within_group(
            sessions.c.duration_seconds
        )
    ranked = (
        select(
            sessions.c.test_id,
            sessions.c.duration_seconds,
            func.row_number()
            .over(
                partition_by=sessions.c.test_id,
                order_by=sessions.c.duration_seconds,
            )
            .label("rn"),
            func.count().over(partition_by=sessions.c.test_id).label("cnt"),
        )
        .where(sessions.c.duration_seconds.is_not(None))
        .subquery()
    )
    median_sq = (
        select(
            ranked.c.test_id.label("test_id"),
            func.avg(ranked.c.duration_seconds).label("median_duration"),
        )
        # Middle row (odd cnt: 2rn-cnt == 1) or the two middle rows averaged
        # (even cnt: 2rn-cnt == 0 and 2). Pure integer arithmetic — SQLAlchemy
        # renders `/ 2` as float division, which would skip the lower-middle
        # row (rn == 1.5 never matches).
        .where((2 * ranked.c.rn - ranked.c.cnt).between(0, 2))
        .group_by(ranked.c.test_id)
        .subquery()
    )
    return median_sq, func.min(median_sq.c.median_duration)


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
                TmsSession.needs_grading,
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
    async def aggregate_by_test(
        db: AsyncSession, query: AggregateQuery, pass_threshold: float
    ):
        """Per-test aggregates over SUBMITTED sessions, GROUP BY test_id.

        One statement: attempt count, distinct candidate count, avg score,
        pass rate (share of attempts at/above ``pass_threshold``), median
        time-to-complete (percentile_cont on Postgres — see
        ``_median_duration_parts``). ``min_attempts`` becomes a HAVING clause.
        """
        score_sq = _session_score_subquery()
        base = (
            select(
                TmsSession.session_id,
                TmsSession.test_id,
                TmsSession.user_id,
                score_sq.c.score,
                _duration_seconds(db).label("duration_seconds"),
            )
            .outerjoin(score_sq, score_sq.c.session_id == TmsSession.session_id)
            .where(TmsSession.status == SessionStatus.SUBMITTED)
        )
        sessions = ReportRepository._apply_filters(base, query).subquery()

        median_join, median_col = _median_duration_parts(db, sessions)
        stmt = (
            select(
                sessions.c.test_id,
                TmsTest.name.label("test_name"),
                func.count(sessions.c.session_id).label("total_attempts"),
                func.count(distinct(sessions.c.user_id)).label(
                    "distinct_candidates"
                ),
                func.avg(sessions.c.score).label("avg_score"),
                (
                    func.avg(
                        case((sessions.c.score >= pass_threshold, 1.0), else_=0.0)
                    )
                    * 100
                ).label("pass_rate"),
                median_col.label("median_duration_seconds"),
            )
            .join(TmsTest, TmsTest.id == sessions.c.test_id)
            .group_by(sessions.c.test_id, TmsTest.name)
            .order_by(sessions.c.test_id)
        )
        if median_join is not None:
            stmt = stmt.outerjoin(
                median_join, median_join.c.test_id == sessions.c.test_id
            )
        if query.min_attempts is not None:
            stmt = stmt.having(
                func.count(sessions.c.session_id) >= query.min_attempts
            )
        result = await db.execute(stmt)
        return list(result.all())

    @staticmethod
    async def attempts_timeseries(db: AsyncSession, query):
        """Attempt volume per (day, test) over SUBMITTED sessions.

        GROUP BY date(submitted_at), test_id — ``func.date`` is portable
        across Postgres and the aiosqlite fixture. Reuses ``_apply_filters``
        (test_id + date range), so the same filters drive this and
        ``/aggregate``. Ordered (date, test_id) for stable client rendering.
        """
        day = func.date(TmsSession.submitted_at).label("date")
        base = (
            select(
                day,
                TmsSession.test_id,
                TmsTest.name.label("test_name"),
                func.count(TmsSession.session_id).label("attempts"),
            )
            .join(TmsTest, TmsTest.id == TmsSession.test_id)
            .where(TmsSession.status == SessionStatus.SUBMITTED)
        )
        base = ReportRepository._apply_filters(base, query)
        stmt = base.group_by(day, TmsSession.test_id, TmsTest.name).order_by(
            day, TmsSession.test_id
        )
        result = await db.execute(stmt)
        return list(result.all())

    @staticmethod
    async def get_test(db: AsyncSession, test_id: int):
        result = await db.execute(select(TmsTest).where(TmsTest.id == test_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def question_difficulty(db: AsyncSession, test_id: int):
        """Per-question difficulty for one test's SUBMITTED sessions.

        Inner GROUP BY question_id (the stable Mongo id — question_index
        varies per session): attempt count, correct-answer rate, and a
        4-bucket histogram of the [0, 1] partial-credit scores via
        sum(case(...)) — portable across both dialects. The outer select adds
        RANK() OVER (ORDER BY correct_rate ASC), so rank 1 = hardest; ties
        share a rank.
        """
        per_question = (
            select(
                TmsAnswer.question_id,
                func.count(TmsAnswer.id).label("attempts"),
                (
                    func.avg(case((TmsAnswer.is_correct, 1.0), else_=0.0)) * 100
                ).label("correct_rate"),
                func.sum(case((TmsAnswer.score < 0.25, 1), else_=0)).label(
                    "bucket_0_25"
                ),
                func.sum(
                    case(
                        (
                            and_(TmsAnswer.score >= 0.25, TmsAnswer.score < 0.5),
                            1,
                        ),
                        else_=0,
                    )
                ).label("bucket_25_50"),
                func.sum(
                    case(
                        (
                            and_(TmsAnswer.score >= 0.5, TmsAnswer.score < 0.75),
                            1,
                        ),
                        else_=0,
                    )
                ).label("bucket_50_75"),
                func.sum(case((TmsAnswer.score >= 0.75, 1), else_=0)).label(
                    "bucket_75_100"
                ),
            )
            .join(TmsSession, TmsSession.session_id == TmsAnswer.session_id)
            .where(
                TmsSession.test_id == test_id,
                TmsSession.status == SessionStatus.SUBMITTED,
            )
            .group_by(TmsAnswer.question_id)
            .subquery()
        )
        stmt = select(
            per_question,
            func.rank()
            .over(order_by=per_question.c.correct_rate.asc())
            .label("difficulty_rank"),
        ).order_by(per_question.c.correct_rate.asc(), per_question.c.question_id)
        result = await db.execute(stmt)
        return list(result.all())

    @staticmethod
    def _apply_filters(stmt: Select, query) -> Select:
        """Shared filter semantics for AttemptsQuery and AggregateQuery
        (the latter has no status filter — aggregates are SUBMITTED-only)."""
        if query.test_id is not None:
            stmt = stmt.where(TmsSession.test_id == query.test_id)
        if getattr(query, "status", None) is not None:
            stmt = stmt.where(TmsSession.status == query.status)
        # Date range bounds the attempt start (exists for every status);
        # `to` is inclusive of the full end date.
        if query.date_from is not None:
            stmt = stmt.where(func.date(TmsSession.started_at) >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(func.date(TmsSession.started_at) <= query.date_to)
        return stmt
