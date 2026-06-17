"""Trainer/admin analytics endpoints.

Read-only aggregation over test-management submission data. No answer keys or
secrets are read or logged — only submission scores and statuses.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query

from src.analytics.stats import (
    COMPLETED_STATUSES,
    completion_rate,
    effective_score,
    score_stats,
    status_breakdown,
)
from src.clients import test_management_client as tm
from src.schemas.report_schema import (
    AttemptEntry,
    CandidateReport,
    OverviewReport,
    PaginatedAttempts,
    ParticipantReport,
    ParticipantTestEntry,
    ScoreStats,
    TestReport,
)
from src.utils.dependencies import (
    require_self_or_privileged,
    require_trainer_or_admin,
)

# Attempt sort keys -> the AttemptEntry field they read.
_SORT_FIELDS = {
    "submitted_at": "submitted_at",
    "assigned_at": "assigned_at",
    "score": "score",
    "test_name": "test_name",
    "status": "status",
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _forward_headers(user: Dict, x_correlation_id: Optional[str], x_request_id: Optional[str]) -> Dict[str, str]:
    """Propagate the caller's verified identity + a correlation id upstream."""
    headers: Dict[str, str] = {}
    if user.get("id"):
        headers["X-User-Id"] = str(user["id"])
    if user.get("email"):
        headers["X-User-Email"] = str(user["email"])
    if user.get("role"):
        headers["X-User-Role"] = str(user["role"])
    cid = x_correlation_id or x_request_id
    if cid:
        headers["X-Correlation-Id"] = cid
    return headers


def _test_name(submission: Dict) -> Optional[str]:
    test = submission.get("test") or {}
    return test.get("name")


@router.get(
    "/overview",
    response_model=OverviewReport,
    summary="Platform-wide analytics overview",
)
async def overview(
    user: Dict = Depends(require_trainer_or_admin),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> OverviewReport:
    headers = _forward_headers(user, x_correlation_id, x_request_id)
    submissions = await tm.list_submissions(headers)
    tests = await tm.list_tests(headers)

    return OverviewReport(
        total_tests=len(tests),
        total_submissions=len(submissions),
        by_status=status_breakdown(submissions),
        completion_rate=completion_rate(submissions),
        score=ScoreStats(**score_stats([effective_score(s) for s in submissions])),
    )


@router.get(
    "/tests/{test_id}",
    response_model=TestReport,
    summary="Per-test analytics",
)
async def test_report(
    test_id: int,
    user: Dict = Depends(require_trainer_or_admin),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> TestReport:
    headers = _forward_headers(user, x_correlation_id, x_request_id)
    submissions = await tm.list_submissions(headers)
    mine = [s for s in submissions if s.get("test_id") == test_id]

    name = next((_test_name(s) for s in mine if _test_name(s)), None)
    if name is None:
        tests = await tm.list_tests(headers)
        name = next((t.get("name") for t in tests if t.get("id") == test_id), None)

    return TestReport(
        test_id=test_id,
        name=name,
        submission_count=len(mine),
        by_status=status_breakdown(mine),
        completion_rate=completion_rate(mine),
        score=ScoreStats(**score_stats([effective_score(s) for s in mine])),
    )


@router.get(
    "/participants/{user_id}",
    response_model=ParticipantReport,
    summary="Per-participant analytics",
)
async def participant_report(
    user_id: int,
    user: Dict = Depends(require_trainer_or_admin),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> ParticipantReport:
    headers = _forward_headers(user, x_correlation_id, x_request_id)
    submissions = await tm.list_submissions(headers)
    mine = [s for s in submissions if s.get("user_id") == user_id]

    entries = [
        ParticipantTestEntry(
            test_id=s.get("test_id"),
            name=_test_name(s),
            status=str(s.get("status")) if s.get("status") is not None else None,
            final_score=effective_score(s),
        )
        for s in mine
    ]
    avg = score_stats([effective_score(s) for s in mine])["average"]

    return ParticipantReport(
        user_id=user_id,
        assigned=len(mine),
        completed=sum(1 for s in mine if str(s.get("status")) in {"COMPLETED", "EVALUATED", "GRADED"}),
        average_final_score=avg,
        tests=entries,
    )


# --- Candidate-facing reporting (self-read or trainer/admin) ------------------


def _attempt_entry(submission: Dict[str, Any]) -> AttemptEntry:
    return AttemptEntry(
        submission_id=submission.get("id"),
        test_id=submission.get("test_id"),
        test_name=_test_name(submission),
        status=str(submission.get("status")) if submission.get("status") is not None else None,
        score=effective_score(submission),
        assigned_at=submission.get("assigned_at"),
        submitted_at=submission.get("submitted_at"),
    )


def _sort_attempts(items: List[AttemptEntry], field: str, descending: bool) -> List[AttemptEntry]:
    """Stable sort that always pushes missing values to the end.

    None never compares against a real value (TypeError on mixed types and the
    sort would be meaningless anyway), so we partition first.
    """
    attr = _SORT_FIELDS[field]
    present = [i for i in items if getattr(i, attr) is not None]
    missing = [i for i in items if getattr(i, attr) is None]
    present.sort(key=lambda i: getattr(i, attr), reverse=descending)
    return present + missing


@router.get(
    "/user/{user_id}",
    response_model=CandidateReport,
    summary="Candidate report (self or trainer/admin)",
)
async def candidate_report(
    user_id: int,
    user: Dict = Depends(require_self_or_privileged),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> CandidateReport:
    headers = _forward_headers(user, x_correlation_id, x_request_id)
    submissions = await tm.list_submissions(headers)
    mine = [s for s in submissions if s.get("user_id") == user_id]

    scores = [effective_score(s) for s in mine]
    stats = score_stats(scores)

    return CandidateReport(
        user_id=user_id,
        assigned=len(mine),
        completed=sum(1 for s in mine if str(s.get("status")) in COMPLETED_STATUSES),
        in_progress=sum(1 for s in mine if str(s.get("status")) == "IN_PROGRESS"),
        by_status=status_breakdown(mine),
        average_final_score=stats["average"],
        best_score=stats["max"],
        score=ScoreStats(**stats),
    )


@router.get(
    "/user/{user_id}/attempts",
    response_model=PaginatedAttempts,
    summary="Candidate attempts — paginated, filterable, sortable",
)
async def candidate_attempts(
    user_id: int,
    user: Dict = Depends(require_self_or_privileged),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by submission status"),
    sort: str = Query("submitted_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> PaginatedAttempts:
    sort_key = sort if sort in _SORT_FIELDS else "submitted_at"

    headers = _forward_headers(user, x_correlation_id, x_request_id)
    submissions = await tm.list_submissions(headers)
    mine = [s for s in submissions if s.get("user_id") == user_id]

    if status:
        wanted = status.upper()
        mine = [s for s in mine if str(s.get("status")).upper() == wanted]

    entries = _sort_attempts(
        [_attempt_entry(s) for s in mine], sort_key, descending=(order == "desc")
    )

    total = len(entries)
    start = (page - 1) * page_size
    items = entries[start : start + page_size]

    return PaginatedAttempts(
        user_id=user_id,
        total=total,
        page=page,
        page_size=page_size,
        sort=sort_key,
        order=order,
        status=status,
        items=items,
    )
