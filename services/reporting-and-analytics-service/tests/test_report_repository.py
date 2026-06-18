"""Repository tests for ReportRepository against seeded in-memory SQLite."""
import pytest
from src.models.session_mirror import AttemptStatus
from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import AttemptFilters

from tests.conftest import OTHER_USER_ID, USER_ID

# ── Aggregate summary ─────────────────────────────────────────────────────────


async def test_summary_aggregates_match_seeded_dataset(db):
    total, avg, best, time_spent, most_recent = (
        await ReportRepository.get_user_summary(db, USER_ID)
    )
    assert total == 4
    assert avg == pytest.approx(72.5)
    assert best == 90.0
    assert time_spent == 750
    assert most_recent is not None
    assert most_recent.session_id == "a4"  # most recent by created_at


async def test_summary_for_user_with_no_attempts_is_zeroed(db):
    total, avg, best, time_spent, most_recent = (
        await ReportRepository.get_user_summary(db, 99999)
    )
    assert total == 0
    assert avg == 0.0
    assert best == 0.0
    assert time_spent == 0
    assert most_recent is None


async def test_summary_is_isolated_per_user(db):
    total, _, best, time_spent, _ = await ReportRepository.get_user_summary(
        db, OTHER_USER_ID
    )
    assert total == 1
    assert best == 10.0
    assert time_spent == 999


# ── Pagination meta ───────────────────────────────────────────────────────────


async def test_pagination_returns_correct_page_and_total(db):
    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(page=1, size=2)
    )
    assert total == 4
    assert len(items) == 2


async def test_pagination_second_page_has_remaining_items(db):
    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(page=2, size=3)
    )
    assert total == 4
    assert len(items) == 1


# ── Filters ───────────────────────────────────────────────────────────────────


async def test_filter_by_test_id(db):
    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(test_id="t1")
    )
    assert total == 2
    assert {i.session_id for i in items} == {"a1", "a2"}


async def test_filter_by_status(db):
    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(status=AttemptStatus.COMPLETED)
    )
    assert total == 2
    assert {i.session_id for i in items} == {"a1", "a4"}


async def test_filter_by_date_from_is_inclusive(db):
    from datetime import date

    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(date_from=date(2026, 6, 5))
    )
    # a2 (06-05), a3 (06-10), a4 (06-15)
    assert total == 3
    assert "a1" not in {i.session_id for i in items}


async def test_filter_by_date_to_is_inclusive(db):
    from datetime import date

    items, total = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(date_to=date(2026, 6, 5))
    )
    # a1 (06-01), a2 (06-05)
    assert total == 2
    assert {i.session_id for i in items} == {"a1", "a2"}


# ── Sorting ───────────────────────────────────────────────────────────────────


async def test_sort_by_score_desc(db):
    items, _ = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(sort="score:desc")
    )
    scores = [i.score for i in items]
    assert scores == sorted(scores, reverse=True)
    assert items[0].session_id == "a2"  # score 90


async def test_sort_by_score_asc(db):
    items, _ = await ReportRepository.list_attempts(
        db, USER_ID, AttemptFilters(sort="score:asc")
    )
    assert items[0].session_id == "a3"  # score 50


async def test_invalid_sort_field_raises(db):
    with pytest.raises(ValueError):
        await ReportRepository.list_attempts(
            db, USER_ID, AttemptFilters(sort="bogus:desc")
        )
