# src/services/reports_service.py
"""Business logic for candidate reporting: map repository rows into the
response envelopes the frontend renders without any client-side re-aggregation.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import reports_repository as repo
from src.schemas.reports_schema import (
    AttemptItem,
    AttemptsPage,
    AttemptsQuery,
    MostRecentAttempt,
    UserSummary,
)


async def get_user_summary(db: AsyncSession, user_id: int) -> UserSummary:
    row = await repo.user_summary(db, user_id)

    most_recent = None
    if row.recent_session_id is not None:
        most_recent = MostRecentAttempt(
            session_id=row.recent_session_id,
            test_id=row.recent_test_id,
            test_name=row.recent_test_name,
            status=row.recent_status,
            submitted_at=row.recent_submitted_at,
            score=row.recent_score,
        )

    return UserSummary(
        user_id=user_id,
        total_attempts=int(row.total_attempts or 0),
        avg_score=row.avg_score,
        best_score=row.best_score,
        total_time_seconds=row.total_time_seconds,
        most_recent=most_recent,
    )


async def get_user_attempts(db: AsyncSession, user_id: int, q: AttemptsQuery) -> AttemptsPage:
    rows, total = await repo.user_attempts(db, user_id, q)
    items = [
        AttemptItem(
            session_id=r.session_id,
            test_id=r.test_id,
            test_name=r.test_name,
            status=r.status,
            questions_answered=int(r.answered or 0),
            started_at=r.started_at,
            submitted_at=r.submitted_at,
            duration_seconds=r.duration_seconds,
            score=r.score,
        )
        for r in rows
    ]
    return AttemptsPage(items=items, total=total, page=q.page, size=q.size)
