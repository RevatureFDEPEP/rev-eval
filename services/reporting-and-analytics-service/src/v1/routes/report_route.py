from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.report_schema import AttemptFilter, PaginatedAttemptsResponse, UserSummaryResponse
from src.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/user/{user_id}", response_model=UserSummaryResponse)
async def get_user_summary(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await ReportService.get_user_summary(db, user_id)


@router.get("/user/{user_id}/attempts", response_model=PaginatedAttemptsResponse)
async def get_user_attempts(
    user_id: int,
    filters: AttemptFilter = Depends(),
    db: AsyncSession = Depends(get_db),
):
    return await ReportService.list_attempts(db, user_id, filters)
