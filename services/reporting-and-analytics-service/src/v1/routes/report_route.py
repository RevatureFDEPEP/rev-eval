from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.report_schema import (
    AggregateReportResponse,
    QueryParams,
    RankingsResponse,
    TestSummary,
    UserReportResponse,
)
from src.services.report_service import ReportService
from src.utils.dependencies import get_current_trainer, get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/tests/{test_id}",
    response_model=TestSummary,
    summary="Per-test analytics report",
)
async def get_test_report(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    _: Dict = Depends(get_current_trainer),
):
    result = await ReportService.get_test_summary(db, test_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Test {test_id} not found")
    return result


@router.get(
    "/aggregate",
    response_model=AggregateReportResponse,
    summary="Aggregate analytics across all active tests",
)
async def get_aggregate_reports(
    params: QueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _: Dict = Depends(get_current_trainer),
):
    total, tests = await ReportService.get_aggregate_reports(db, params)
    return AggregateReportResponse(
        total_tests=total,
        page=params.page,
        page_size=params.page_size,
        tests=tests,
    )


@router.get(
    "/tests/{test_id}/rankings",
    response_model=RankingsResponse,
    summary="Ranked leaderboard for a test",
)
async def get_test_rankings(
    test_id: int,
    params: QueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _: Dict = Depends(get_current_trainer),
):
    rankings = await ReportService.get_rankings(db, test_id, params)
    return RankingsResponse(
        test_id=test_id,
        page=params.page,
        page_size=params.page_size,
        rankings=rankings,
    )


@router.get(
    "/user/{user_id}",
    response_model=UserReportResponse,
    summary="Completed sessions for a candidate (results page feed)",
)
async def get_user_report(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current: Dict = Depends(get_current_user),
):
    role = (current.get("role") or "").upper()
    if role != "TRAINER" and current["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: can only view your own results",
        )
    sessions = await ReportService.get_user_sessions(db, user_id)
    return UserReportResponse(user_id=user_id, sessions=sessions)
