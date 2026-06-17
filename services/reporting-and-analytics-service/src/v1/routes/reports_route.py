"""Candidate reporting endpoints (W4-F1).

Authorization is header-trust, matching the platform contract: the API gateway
verifies the JWT and injects ``X-User-Id`` / ``X-User-Role``; this service never
decodes JWTs. ``require_self_or_trainer`` enforces that a participant may read
only their own reports while a trainer may read anyone's. (W4-F3 will extend the
trainer surface with aggregate endpoints; the gate established here is reused.)
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.reporting_schema import (
    AttemptsQuery,
    PaginatedAttempts,
    UserSummaryResponse,
)
from src.services.reporting_service import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"])


def require_self_or_trainer(
    user_id: int,
    x_user_id: str | None = Header(None),
    x_user_role: str | None = Header(None),
) -> None:
    """Allow trainers to read any user's reports; participants only their own.

    Identity is taken from the gateway-injected headers, never a client claim.
    A caller with no gateway headers (e.g. bypassing the gateway) is denied.
    """
    if x_user_role and x_user_role.upper() == "TRAINER":
        return
    if x_user_id is not None and x_user_id == str(user_id):
        return
    raise HTTPException(
        status_code=403, detail="Not authorized to view this user's reports"
    )


@router.get("/user/{user_id}", response_model=UserSummaryResponse)
async def get_user_summary(
    user_id: int,
    _: None = Depends(require_self_or_trainer),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate results summary for one candidate."""
    return await ReportingService.get_user_summary(db, user_id)


@router.get("/user/{user_id}/attempts", response_model=PaginatedAttempts)
async def get_user_attempts(
    user_id: int,
    q: AttemptsQuery = Depends(),
    _: None = Depends(require_self_or_trainer),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable attempt history for one candidate."""
    return await ReportingService.get_user_attempts(db, user_id, q)
