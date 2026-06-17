"""Business logic for candidate reporting: assemble envelopes from repo rows."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tms_readonly import QuizSessionStatus
from src.repositories.reporting_repository import ReportingRepository
from src.schemas.reporting_schema import (
    AttemptItem,
    AttemptsQuery,
    PaginatedAttempts,
    UserSummaryResponse,
)


def _raw_score(points_sum, max_sum) -> float | None:
    """The one score definition: points_earned / max_points over a session's
    answers. None when there are no answers (max_sum is None) or max is 0."""
    if max_sum is None or max_sum == 0:
        return None
    return points_sum / max_sum


def _score_fraction(points_sum, max_sum) -> float | None:
    """Display score: the raw fraction rounded to 4dp."""
    raw = _raw_score(points_sum, max_sum)
    return round(raw, 4) if raw is not None else None


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
        rows = await ReportingRepository.fetch_user_session_rollup(db, user_id)

        # Score and time count only SUBMITTED (completed) attempts. ACTIVE
        # (in-progress) and EXPIRED (timed-out) sessions are still attempts but
        # would skew a candidate's average, so they're excluded from score stats.
        submitted = [r for r in rows if r.status == QuizSessionStatus.SUBMITTED]
        raw_scores = [
            s
            for s in (_raw_score(r.points_sum, r.max_sum) for r in submitted)
            if s is not None
        ]
        total_time = sum(
            _duration_seconds(r.started_at, r.submitted_at) or 0 for r in submitted
        )
        dated = [r for r in rows if r.created_at is not None]
        most_recent = max(dated, key=lambda r: r.created_at) if dated else None

        return UserSummaryResponse(
            user_id=user_id,
            total_attempts=len(rows),
            average_score=(
                round(sum(raw_scores) / len(raw_scores), 4) if raw_scores else None
            ),
            best_score=round(max(raw_scores), 4) if raw_scores else None,
            total_time_spent_seconds=total_time,
            most_recent_attempt=(
                _row_to_attempt(most_recent) if most_recent is not None else None
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
