from typing import List, Optional, Tuple

from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.reporting_models import QuizSession, Test
from src.schemas.report_schema import AttemptsQueryParams, QueryParams

_VALID_ATTEMPTS_SORT_COLS = {"completed_at", "percentage_score", "test_id"}

_VALID_SORT_COLS = {"avg_score", "attempt_count", "test_name"}


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_test_summary(self, test_id: int) -> Optional[dict]:
        result = await self.db.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()
        if test is None:
            return None

        threshold = settings.PASS_THRESHOLD
        agg_stmt = select(
            func.count(QuizSession.id).label("attempt_count"),
            func.avg(QuizSession.percentage_score).label("avg_score"),
            func.count(case((QuizSession.percentage_score >= threshold, 1))).label("pass_count"),
        ).where(
            QuizSession.test_id == test_id,
            QuizSession.status == "COMPLETED",
            QuizSession.percentage_score.isnot(None),
        )
        row = (await self.db.execute(agg_stmt)).one()

        attempt_count = row.attempt_count or 0
        avg_score = float(row.avg_score) if row.avg_score is not None else None
        pass_count = row.pass_count or 0
        pass_rate = pass_count / attempt_count if attempt_count > 0 else None

        scores_stmt = select(QuizSession.percentage_score).where(
            QuizSession.test_id == test_id,
            QuizSession.status == "COMPLETED",
            QuizSession.percentage_score.isnot(None),
        )
        scores = [r[0] for r in (await self.db.execute(scores_stmt)).fetchall()]
        distribution: dict = {"0-49": 0, "50-69": 0, "70-89": 0, "90-100": 0}
        for s in scores:
            if s < 50:
                distribution["0-49"] += 1
            elif s < 70:
                distribution["50-69"] += 1
            elif s < 90:
                distribution["70-89"] += 1
            else:
                distribution["90-100"] += 1

        return {
            "test_id": test_id,
            "test_name": test.name,
            "attempt_count": attempt_count,
            "avg_score": avg_score,
            "pass_rate": pass_rate,
            "score_distribution": distribution,
        }

    async def get_aggregate_reports(self, params: QueryParams) -> Tuple[int, List[dict]]:
        threshold = settings.PASS_THRESHOLD

        total = (
            await self.db.execute(
                select(func.count(Test.id)).where(Test.active.is_(True))
            )
        ).scalar() or 0

        col_name = params.sort_by if params.sort_by in _VALID_SORT_COLS else "avg_score"
        order_clause = text(f"{col_name} DESC") if params.order == "desc" else text(f"{col_name} ASC")

        agg_stmt = (
            select(
                Test.id.label("test_id"),
                Test.name.label("test_name"),
                func.count(QuizSession.id).label("attempt_count"),
                func.avg(QuizSession.percentage_score).label("avg_score"),
                func.count(case((QuizSession.percentage_score >= threshold, 1))).label("pass_count"),
            )
            .outerjoin(
                QuizSession,
                and_(
                    QuizSession.test_id == Test.id,
                    QuizSession.status == "COMPLETED",
                    QuizSession.percentage_score.isnot(None),
                ),
            )
            .where(Test.active.is_(True))
            .group_by(Test.id, Test.name)
            .order_by(order_clause)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        rows = (await self.db.execute(agg_stmt)).fetchall()
        tests = []
        for row in rows:
            attempt_count = row.attempt_count or 0
            avg_score = float(row.avg_score) if row.avg_score is not None else None
            pass_count = row.pass_count or 0
            pass_rate = pass_count / attempt_count if attempt_count > 0 else None
            tests.append({
                "test_id": row.test_id,
                "test_name": row.test_name,
                "attempt_count": attempt_count,
                "avg_score": avg_score,
                "pass_rate": pass_rate,
                "score_distribution": None,
            })

        return total, tests

    async def get_rankings(self, test_id: int, params: QueryParams) -> List[dict]:
        rank_col = func.rank().over(
            order_by=QuizSession.percentage_score.desc()
        ).label("rank")

        stmt = (
            select(
                QuizSession.user_id,
                QuizSession.percentage_score.label("score"),
                QuizSession.completed_at,
                rank_col,
            )
            .where(
                QuizSession.test_id == test_id,
                QuizSession.status == "COMPLETED",
                QuizSession.percentage_score.isnot(None),
            )
            .order_by(rank_col)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        rows = (await self.db.execute(stmt)).fetchall()
        return [
            {
                "rank": row.rank,
                "user_id": row.user_id,
                "score": float(row.score),
                "completed_at": row.completed_at,
            }
            for row in rows
        ]

    async def get_user_summary(self, user_id: int) -> dict:
        # Aggregate: count, avg, max
        agg_stmt = select(
            func.count(QuizSession.id).label("total_attempts"),
            func.avg(QuizSession.percentage_score).label("avg_score"),
            func.max(QuizSession.percentage_score).label("best_score"),
        ).where(
            QuizSession.user_id == user_id,
            QuizSession.status == "COMPLETED",
            QuizSession.percentage_score.isnot(None),
        )
        agg = (await self.db.execute(agg_stmt)).one()

        # Total time spent: sum (completed_at - started_at) in Python
        time_stmt = select(
            QuizSession.started_at,
            QuizSession.completed_at,
        ).where(
            QuizSession.user_id == user_id,
            QuizSession.status == "COMPLETED",
            QuizSession.started_at.isnot(None),
            QuizSession.completed_at.isnot(None),
        )
        time_rows = (await self.db.execute(time_stmt)).fetchall()
        total_time = sum(
            int((r.completed_at - r.started_at).total_seconds())
            for r in time_rows
            if r.completed_at > r.started_at
        ) or None

        # Most recent session (subquery pattern via LIMIT 1)
        recent_stmt = (
            select(
                QuizSession.id.label("session_id"),
                QuizSession.test_id,
                Test.name.label("test_name"),
                QuizSession.percentage_score,
                QuizSession.completed_at,
                QuizSession.status,
            )
            .join(Test, Test.id == QuizSession.test_id)
            .where(
                QuizSession.user_id == user_id,
                QuizSession.status == "COMPLETED",
            )
            .order_by(QuizSession.completed_at.desc())
            .limit(1)
        )
        recent_row = (await self.db.execute(recent_stmt)).first()
        most_recent = (
            {
                "session_id": recent_row.session_id,
                "test_id": recent_row.test_id,
                "test_name": recent_row.test_name,
                "percentage_score": float(recent_row.percentage_score) if recent_row.percentage_score is not None else None,
                "completed_at": recent_row.completed_at,
                "status": recent_row.status,
            }
            if recent_row
            else None
        )

        return {
            "user_id": user_id,
            "total_attempts": agg.total_attempts or 0,
            "avg_score": float(agg.avg_score) if agg.avg_score is not None else None,
            "best_score": float(agg.best_score) if agg.best_score is not None else None,
            "total_time_spent_seconds": total_time,
            "most_recent": most_recent,
        }

    async def get_user_attempts(self, user_id: int, params: AttemptsQueryParams) -> Tuple[int, List[dict]]:
        col_name = params.sort_by if params.sort_by in _VALID_ATTEMPTS_SORT_COLS else "completed_at"
        order_clause = text(f"{col_name} DESC") if params.order == "desc" else text(f"{col_name} ASC")

        base_filters = [QuizSession.user_id == user_id]
        if params.status:
            base_filters.append(QuizSession.status == params.status.upper())
        if params.test_id is not None:
            base_filters.append(QuizSession.test_id == params.test_id)
        if params.from_date is not None:
            base_filters.append(QuizSession.completed_at >= params.from_date)
        if params.to_date is not None:
            base_filters.append(QuizSession.completed_at <= params.to_date)

        total_stmt = (
            select(func.count(QuizSession.id))
            .join(Test, Test.id == QuizSession.test_id)
            .where(*base_filters)
        )
        total = (await self.db.execute(total_stmt)).scalar() or 0

        rows_stmt = (
            select(
                QuizSession.id.label("session_id"),
                QuizSession.test_id,
                Test.name.label("test_name"),
                QuizSession.percentage_score,
                QuizSession.completed_at,
                QuizSession.status,
            )
            .join(Test, Test.id == QuizSession.test_id)
            .where(*base_filters)
            .order_by(order_clause)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        rows = (await self.db.execute(rows_stmt)).fetchall()
        attempts = [
            {
                "session_id": row.session_id,
                "test_id": row.test_id,
                "test_name": row.test_name,
                "percentage_score": float(row.percentage_score) if row.percentage_score is not None else None,
                "completed_at": row.completed_at,
                "status": row.status,
            }
            for row in rows
        ]
        return total, attempts
