"""Business layer for the candidate results reports (W4-F1).

Shapes repository rows into the response envelopes. Scores are rounded to two
decimals for presentation — all aggregation already happened in SQL.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import (
    AggregateQuery,
    AggregateReport,
    AttemptItem,
    AttemptsPage,
    AttemptsQuery,
    MostRecentAttempt,
    QuestionDifficultyReport,
    QuestionDifficultyRow,
    ScoreHistogram,
    TestAggregateRow,
    TimeseriesPoint,
    TimeseriesQuery,
    TimeseriesReport,
    UserSummary,
)


def _round(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), 2)


class ReportService:
    @staticmethod
    async def user_summary(db: AsyncSession, user_id: int) -> UserSummary:
        row = await ReportRepository.user_summary(db, user_id)
        most_recent = None
        if row.recent_session_id is not None:
            most_recent = MostRecentAttempt(
                session_id=row.recent_session_id,
                test_id=row.recent_test_id,
                test_name=row.recent_test_name,
                submitted_at=row.recent_submitted_at,
                score=_round(row.recent_score),
            )
        return UserSummary(
            user_id=user_id,
            total_attempts=row.total_attempts,
            avg_score=_round(row.avg_score),
            best_score=_round(row.best_score),
            total_time_seconds=_round(row.total_time_seconds),
            most_recent=most_recent,
        )

    @staticmethod
    async def user_attempts(
        db: AsyncSession, user_id: int, query: AttemptsQuery
    ) -> AttemptsPage:
        rows, total = await ReportRepository.user_attempts(db, user_id, query)
        items = [
            AttemptItem(
                session_id=row.session_id,
                test_id=row.test_id,
                test_name=row.test_name,
                status=row.status,
                started_at=row.started_at,
                submitted_at=row.submitted_at,
                duration_seconds=_round(row.duration_seconds),
                score=_round(row.score),
                needs_grading=bool(row.needs_grading),
            )
            for row in rows
        ]
        return AttemptsPage(items=items, total=total, page=query.page, size=query.size)

    @staticmethod
    async def aggregate_by_test(
        db: AsyncSession, query: AggregateQuery
    ) -> AggregateReport:
        threshold = settings.REPORT_PASS_THRESHOLD
        rows = await ReportRepository.aggregate_by_test(db, query, threshold)
        items = [
            TestAggregateRow(
                test_id=row.test_id,
                test_name=row.test_name,
                total_attempts=row.total_attempts,
                distinct_candidates=row.distinct_candidates,
                avg_score=_round(row.avg_score),
                pass_rate=_round(row.pass_rate),
                median_duration_seconds=_round(row.median_duration_seconds),
            )
            for row in rows
        ]
        return AggregateReport(items=items, pass_threshold=threshold)

    @staticmethod
    async def attempts_timeseries(
        db: AsyncSession, query: TimeseriesQuery
    ) -> TimeseriesReport:
        rows = await ReportRepository.attempts_timeseries(db, query)
        items = [
            TimeseriesPoint(
                date=row.date,
                test_id=row.test_id,
                test_name=row.test_name,
                attempts=row.attempts,
            )
            for row in rows
        ]
        return TimeseriesReport(items=items)

    @staticmethod
    async def question_difficulty(
        db: AsyncSession, test_id: int
    ) -> Optional[QuestionDifficultyReport]:
        """None when the test doesn't exist (route turns that into a 404);
        a test with no submitted attempts gets an empty items list."""
        test = await ReportRepository.get_test(db, test_id)
        if test is None:
            return None
        rows = await ReportRepository.question_difficulty(db, test_id)
        items = [
            QuestionDifficultyRow(
                question_id=row.question_id,
                attempts=row.attempts,
                correct_rate=_round(row.correct_rate),
                difficulty_rank=row.difficulty_rank,
                histogram=ScoreHistogram(
                    bucket_0_25=row.bucket_0_25,
                    bucket_25_50=row.bucket_25_50,
                    bucket_50_75=row.bucket_50_75,
                    bucket_75_100=row.bucket_75_100,
                ),
            )
            for row in rows
        ]
        return QuestionDifficultyReport(
            test_id=test.id, test_name=test.name, items=items
        )
