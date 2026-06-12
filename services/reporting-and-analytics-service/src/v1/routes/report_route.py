"""Trainer/admin analytics endpoints.

Read-only aggregation over test-management submission data. No answer keys or
secrets are read or logged — only submission scores and statuses.
"""
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header

from src.analytics.stats import (
    completion_rate,
    effective_score,
    score_stats,
    status_breakdown,
)
from src.clients import test_management_client as tm
from src.schemas.report_schema import (
    OverviewReport,
    ParticipantReport,
    ParticipantTestEntry,
    ScoreStats,
    TestReport,
)
from src.utils.dependencies import require_trainer_or_admin

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
