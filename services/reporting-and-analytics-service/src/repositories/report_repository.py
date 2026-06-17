from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import Session
from src.models.session_answer import SessionAnswer
from src.schemas.report_schema import AttemptFilter


def _build_session_scores_cte():
    """CTE: per-session score_ratio (works on both PostgreSQL and SQLite)."""
    score_ratio_expr = case(
        (func.sum(SessionAnswer.max_points) > 0,
         func.sum(SessionAnswer.earned_points) / func.sum(SessionAnswer.max_points)),
        else_=None,
    )

    return (
        select(
            Session.session_id,
            Session.test_id,
            Session.user_id,
            Session.status,
            Session.server_now,
            Session.submitted_at,
            Session.expires_at,
            score_ratio_expr.label("score_ratio"),
        )
        .outerjoin(SessionAnswer, SessionAnswer.session_id == Session.session_id)
        .group_by(
            Session.session_id,
            Session.test_id,
            Session.user_id,
            Session.status,
            Session.server_now,
            Session.submitted_at,
            Session.expires_at,
        )
        .cte("session_scores")
    )


class ReportRepository:

    @staticmethod
    async def get_user_summary(db: AsyncSession, user_id: int) -> dict[str, Any]:
        session_scores = _build_session_scores_cte()

        stats_stmt = select(
            func.count().label("total_attempts"),
            func.avg(session_scores.c.score_ratio).label("average_score"),
            func.max(session_scores.c.score_ratio).label("best_score"),
        ).where(session_scores.c.user_id == user_id)

        # Fetch completed sessions to compute total_time_spent in Python
        # This avoids dialect-specific EXTRACT(EPOCH FROM ...) vs julianday() differences
        time_stmt = (
            select(Session.submitted_at, Session.server_now)
            .where(
                Session.user_id == user_id,
                Session.submitted_at.isnot(None),
            )
        )

        recent_stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.server_now.desc())
            .limit(1)
        )

        stats_result = await db.execute(stats_stmt)
        stats_row = stats_result.one()

        time_result = await db.execute(time_stmt)
        time_rows = time_result.all()

        recent_result = await db.execute(recent_stmt)
        recent_session = recent_result.scalars().first()

        total_time_spent: float | None = None
        if time_rows:
            seconds_sum = sum(
                (row.submitted_at - row.server_now).total_seconds()
                for row in time_rows
            )
            total_time_spent = seconds_sum

        recent_score_ratio = None
        if recent_session is not None:
            score_subq = select(
                case(
                    (func.sum(SessionAnswer.max_points) > 0,
                     func.sum(SessionAnswer.earned_points) / func.sum(SessionAnswer.max_points)),
                    else_=None,
                ).label("score_ratio")
            ).where(SessionAnswer.session_id == recent_session.session_id)
            score_result = await db.execute(score_subq)
            recent_score_ratio = score_result.scalar()

        return {
            "total_attempts": stats_row.total_attempts or 0,
            "average_score": stats_row.average_score,
            "best_score": stats_row.best_score,
            "total_time_spent": total_time_spent,
            "most_recent_session": recent_session,
            "most_recent_score_ratio": recent_score_ratio,
        }

    @staticmethod
    async def list_attempts(
        db: AsyncSession,
        user_id: int,
        filters: AttemptFilter,
    ) -> tuple[list[dict[str, Any]], int]:
        session_scores = _build_session_scores_cte()

        # Build filter conditions
        base_stmt = select(session_scores).where(session_scores.c.user_id == user_id)
        count_stmt = select(func.count()).select_from(session_scores).where(
            session_scores.c.user_id == user_id
        )

        if filters.test_id is not None:
            base_stmt = base_stmt.where(session_scores.c.test_id == filters.test_id)
            count_stmt = count_stmt.where(session_scores.c.test_id == filters.test_id)
        if filters.from_date is not None:
            base_stmt = base_stmt.where(session_scores.c.server_now >= filters.from_date)
            count_stmt = count_stmt.where(session_scores.c.server_now >= filters.from_date)
        if filters.to_date is not None:
            cutoff = filters.to_date + timedelta(days=1)
            base_stmt = base_stmt.where(session_scores.c.server_now < cutoff)
            count_stmt = count_stmt.where(session_scores.c.server_now < cutoff)
        if filters.status is not None:
            status_val = filters.status.value if hasattr(filters.status, "value") else filters.status
            base_stmt = base_stmt.where(session_scores.c.status == status_val)
            count_stmt = count_stmt.where(session_scores.c.status == status_val)

        # Sort
        _sort_map = {
            "server_now": session_scores.c.server_now,
            "submitted_at": session_scores.c.submitted_at,
            "expires_at": session_scores.c.expires_at,
            "score_ratio": session_scores.c.score_ratio,
        }
        sort_field, sort_dir = filters.sort.split(":", 1)
        sort_col = _sort_map.get(sort_field, session_scores.c.server_now)
        order_expr = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

        size = min(filters.size, 100)
        offset = (filters.page - 1) * size

        base_stmt = base_stmt.order_by(order_expr).offset(offset).limit(size)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        data_result = await db.execute(base_stmt)
        rows = data_result.mappings().all()

        return [dict(row) for row in rows], total
