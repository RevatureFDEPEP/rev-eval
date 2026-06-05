from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.report_schemas import DashboardReport, ParticipantReport, SkillSummary, TestReport
from src.services import report_service
from src.utils.dependencies import get_current_user, require_trainer

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard", response_model=DashboardReport)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_trainer),
):
    return await report_service.get_dashboard(db)


@router.get("/tests/{test_id}", response_model=TestReport)
async def test_report(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_trainer),
):
    report = await report_service.get_test_report(db, test_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
    return report


@router.get("/participants/{user_id}", response_model=ParticipantReport)
async def participant_report(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    role = (current_user.get("role") or "").upper()
    caller_id = current_user.get("user_id")
    if role != "TRAINER" and str(caller_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await report_service.get_participant_report(db, user_id)


@router.get("/skills", response_model=list[SkillSummary])
async def skills_report(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_trainer),
):
    return await report_service.get_skills_report(db)
