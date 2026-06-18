from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import AttemptsQueryParams, QueryParams


class ReportService:
    @staticmethod
    async def get_test_summary(db: AsyncSession, test_id: int) -> Optional[dict]:
        return await ReportRepository(db).get_test_summary(test_id)

    @staticmethod
    async def get_aggregate_reports(db: AsyncSession, params: QueryParams) -> Tuple[int, List[dict]]:
        return await ReportRepository(db).get_aggregate_reports(params)

    @staticmethod
    async def get_rankings(db: AsyncSession, test_id: int, params: QueryParams) -> List[dict]:
        return await ReportRepository(db).get_rankings(test_id, params)

    @staticmethod
    async def get_user_summary(db: AsyncSession, user_id: int) -> dict:
        return await ReportRepository(db).get_user_summary(user_id)

    @staticmethod
    async def get_user_attempts(db: AsyncSession, user_id: int, params: AttemptsQueryParams) -> Tuple[int, List[dict]]:
        return await ReportRepository(db).get_user_attempts(user_id, params)

    @staticmethod
    async def get_test_question_stats(db: AsyncSession, test_id: int):
        return await ReportRepository(db).get_test_question_stats(test_id)
