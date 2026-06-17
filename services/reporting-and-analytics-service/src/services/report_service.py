from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import (
    AttemptFilter,
    AttemptItem,
    PaginatedAttemptsResponse,
    SessionStatus,
    UserSummaryResponse,
)

_VALID_SORT_FIELDS = {"server_now", "submitted_at", "expires_at", "score_ratio"}
_VALID_SORT_DIRS = {"asc", "desc"}


def _validate_sort(sort: str) -> None:
    parts = sort.split(":")
    if len(parts) != 2 or parts[0] not in _VALID_SORT_FIELDS or parts[1] not in _VALID_SORT_DIRS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort '{sort}'. Expected format: field:direction where "
                   f"field is one of {sorted(_VALID_SORT_FIELDS)} and direction is asc or desc.",
        )


class ReportService:

    @staticmethod
    async def get_user_summary(db: AsyncSession, user_id: int) -> UserSummaryResponse:
        data = await ReportRepository.get_user_summary(db, user_id)

        most_recent: AttemptItem | None = None
        if data["most_recent_session"] is not None:
            s = data["most_recent_session"]
            most_recent = AttemptItem(
                session_id=s.session_id,
                test_id=s.test_id,
                user_id=s.user_id,
                status=SessionStatus(s.status) if isinstance(s.status, str) else s.status,
                server_now=s.server_now,
                submitted_at=s.submitted_at,
                expires_at=s.expires_at,
                score_ratio=data["most_recent_score_ratio"],
            )

        return UserSummaryResponse(
            user_id=user_id,
            total_attempts=data["total_attempts"],
            average_score=data["average_score"],
            best_score=data["best_score"],
            total_time_spent=data["total_time_spent"],
            most_recent_attempt=most_recent,
        )

    @staticmethod
    async def list_attempts(
        db: AsyncSession,
        user_id: int,
        filters: AttemptFilter,
    ) -> PaginatedAttemptsResponse:
        _validate_sort(filters.sort)
        filters.size = min(filters.size, 100)

        rows, total = await ReportRepository.list_attempts(db, user_id, filters)

        items = [
            AttemptItem(
                session_id=row["session_id"],
                test_id=row["test_id"],
                user_id=row["user_id"],
                status=SessionStatus(row["status"]) if isinstance(row["status"], str) else row["status"],
                server_now=row["server_now"],
                submitted_at=row.get("submitted_at"),
                expires_at=row["expires_at"],
                score_ratio=row.get("score_ratio"),
            )
            for row in rows
        ]

        return PaginatedAttemptsResponse(
            items=items,
            total=total,
            page=filters.page,
            size=filters.size,
        )
