"""Business logic for candidate reporting: assemble envelopes from repo rows."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.reporting_repository import ReportingRepository
from src.schemas.reporting_schema import (
    AttemptItem,
    AttemptsQuery,
    PaginatedAttempts,
    UserSummaryResponse,
)


def _score_fraction(points_sum, max_sum) -> float | None:
    if max_sum is None or max_sum == 0:
        return None
    return round(points_sum / max_sum, 4)


def _duration_seconds(started_at, submitted_at) -> int | None:
    if started_at is None or submitted_at is None:
        return None
    return max(0, int((submitted_at - started_at).total_seconds()))


def _row_to_attempt(row) -> AttemptItem:
    return AttemptItem(
        session_id=row.session_id,
        test_id=row.test_id,
        test_name=row.test_name,
        status=row.status,
        score=_score_fraction(row.points_sum, row.max_sum),
        correct_count=row.correct_count,
        total_answered=row.total_answered,
        started_at=row.started_at,
        submitted_at=row.submitted_at,
        time_spent_seconds=_duration_seconds(row.started_at, row.submitted_at),
    )


class ReportingService:
    @staticmethod
    async def get_user_summary(db: AsyncSession, user_id: int) -> UserSummaryResponse:
        agg = await ReportingRepository.fetch_score_aggregates(db, user_id)
        durations = await ReportingRepository.fetch_session_durations(db, user_id)
        recent_row = await ReportingRepository.fetch_most_recent_attempt(db, user_id)

        total_time = sum(_duration_seconds(s, sub) or 0 for s, sub in durations)
        return UserSummaryResponse(
            user_id=user_id,
            total_attempts=int(agg.total_attempts or 0),
            average_score=(
                round(agg.average_score, 4) if agg.average_score is not None else None
            ),
            best_score=(
                round(agg.best_score, 4) if agg.best_score is not None else None
            ),
            total_time_spent_seconds=total_time,
            most_recent_attempt=(
                _row_to_attempt(recent_row) if recent_row is not None else None
            ),
        )

    @staticmethod
    async def get_user_attempts(
        db: AsyncSession, user_id: int, q: AttemptsQuery
    ) -> PaginatedAttempts:
        rows, total = await ReportingRepository.fetch_attempts(db, user_id, q)
        return PaginatedAttempts(
            items=[_row_to_attempt(r) for r in rows],
            total=total,
            page=q.page,
            size=q.size,
        )
