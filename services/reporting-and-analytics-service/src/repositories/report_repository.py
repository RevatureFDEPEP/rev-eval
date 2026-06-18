from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.session_mirror import SessionMirror
from src.schemas.report_schema import SORTABLE_FIELDS, AttemptFilters


class ReportRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: str) -> Optional[SessionMirror]:
        result = await db.execute(
            select(SessionMirror).where(SessionMirror.session_id == session_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_summary(
        db: AsyncSession, user_id: int
    ) -> Tuple[int, float, float, int, Optional[SessionMirror]]:
        """Aggregate a user's attempts in a single query.

        Returns (total_attempts, average_score, best_score, total_time_spent,
        most_recent_attempt). Uses func.count/avg/sum/max plus a scalar
        subquery selecting the most recent attempt's id (see ADR 0001).
        """
        most_recent_id_subq = (
            select(SessionMirror.session_id)
            .where(SessionMirror.user_id == user_id)
            .order_by(
                SessionMirror.created_at.desc(),
                SessionMirror.session_id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        stmt = select(
            func.count(SessionMirror.session_id).label("total_attempts"),
            func.avg(SessionMirror.score).label("average_score"),
            func.max(SessionMirror.score).label("best_score"),
            func.sum(SessionMirror.time_spent_seconds).label("total_time_spent"),
            most_recent_id_subq.label("most_recent_id"),
        ).where(SessionMirror.user_id == user_id)

        row = (await db.execute(stmt)).one()

        most_recent = None
        if row.most_recent_id is not None:
            most_recent = await ReportRepository.get_by_id(db, row.most_recent_id)

        return (
            int(row.total_attempts or 0),
            float(row.average_score or 0.0),
            float(row.best_score or 0.0),
            int(row.total_time_spent or 0),
            most_recent,
        )

    @staticmethod
    def _apply_filters(stmt, user_id: int, filters: AttemptFilters):
        stmt = stmt.where(SessionMirror.user_id == user_id)
        if filters.test_id is not None:
            stmt = stmt.where(SessionMirror.test_id == filters.test_id)
        if filters.status is not None:
            stmt = stmt.where(SessionMirror.status == filters.status)
        if filters.date_from is not None:
            start = datetime.combine(filters.date_from, time.min)
            stmt = stmt.where(SessionMirror.created_at >= start)
        if filters.date_to is not None:
            # Inclusive of the whole `to` day.
            end = datetime.combine(filters.date_to, time.min) + timedelta(days=1)
            stmt = stmt.where(SessionMirror.created_at < end)
        return stmt

    @staticmethod
    async def list_attempts(
        db: AsyncSession, user_id: int, filters: AttemptFilters
    ) -> Tuple[List[SessionMirror], int]:
        """Return (items, total) for one filtered, sorted, paginated page."""
        field, direction = filters.sort.split(":")
        if field not in SORTABLE_FIELDS:
            raise ValueError(f"Cannot sort by '{field}'")
        column = getattr(SessionMirror, field)
        order_by = column.desc() if direction == "desc" else column.asc()

        base = ReportRepository._apply_filters(select(SessionMirror), user_id, filters)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        page_stmt = (
            base.order_by(order_by, SessionMirror.session_id.asc())
            .offset((filters.page - 1) * filters.size)
            .limit(filters.size)
        )
        items = list((await db.execute(page_stmt)).scalars().all())
        return items, total
