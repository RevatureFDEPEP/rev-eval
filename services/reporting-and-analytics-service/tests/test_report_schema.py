"""Smoke tests for reporting schemas — no database required."""
from datetime import date, datetime

from src.models.session_mirror import AttemptStatus
from src.schemas.report_schema import (
    SORTABLE_FIELDS,
    AttemptFilters,
    AttemptOut,
    PaginatedAttempts,
    UserReportSummary,
)


def test_attempt_filters_defaults():
    f = AttemptFilters()
    assert f.page == 1
    assert f.size == 20
    assert f.test_id is None
    assert f.date_from is None
    assert f.date_to is None
    assert f.status is None
    assert f.sort == "created_at:desc"


def test_attempt_filters_accepts_values():
    f = AttemptFilters(
        page=2,
        size=50,
        test_id="t9",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        status=AttemptStatus.SUBMITTED,
        sort="score:asc",
    )
    assert f.page == 2
    assert f.size == 50
    assert f.status == AttemptStatus.SUBMITTED


def test_attempt_out_reads_from_orm_attributes():
    class FakeRow:
        session_id = "x"
        user_id = 1
        test_id = "t1"
        status = AttemptStatus.COMPLETED
        score = 88.0
        time_spent_seconds = 120
        started_at = None
        submitted_at = None
        created_at = datetime(2026, 6, 1, 9, 0)

    out = AttemptOut.model_validate(FakeRow())
    assert out.session_id == "x"
    assert out.score == 88.0
    assert out.status == AttemptStatus.COMPLETED


def test_user_report_summary_optional_most_recent():
    s = UserReportSummary(
        user_id=1,
        total_attempts=0,
        average_score=0.0,
        best_score=0.0,
        total_time_spent=0,
    )
    assert s.most_recent_attempt is None


def test_paginated_attempts_envelope_shape():
    p = PaginatedAttempts(items=[], total=0, page=1, size=20, pages=0)
    assert p.items == []
    assert p.total == 0


def test_sortable_fields_contains_expected():
    assert {"created_at", "score", "time_spent_seconds"} <= SORTABLE_FIELDS
