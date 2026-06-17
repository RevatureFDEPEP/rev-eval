"""Unit tests for ReportRepository and ReportService.

All tests run against an in-memory SQLite database via the `db` fixture in
conftest.py.  The Session and SessionAnswer models are created fresh per test.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.session import Session, SessionStatus
from src.models.session_answer import SessionAnswer
from src.repositories.report_repository import ReportRepository
from src.schemas.report_schema import AttemptFilter
from src.services.report_service import ReportService


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _make_session(
    user_id: int,
    test_id: int = 1,
    status: SessionStatus = SessionStatus.COMPLETED,
    server_now: datetime | None = None,
    submitted_at: datetime | None = None,
    offset_seconds: int = 0,
) -> Session:
    base = server_now or datetime(2026, 1, 1, 12, 0, 0) + timedelta(seconds=offset_seconds)
    sub = submitted_at if submitted_at is not None else (
        base + timedelta(minutes=30) if status == SessionStatus.COMPLETED else None
    )
    return Session(
        session_id=uuid.uuid4(),
        test_id=test_id,
        user_id=user_id,
        session_token=uuid.uuid4().hex[:64],
        server_now=base,
        expires_at=base + timedelta(hours=1),
        status=status,
        current_index=0,
        question_ids=[],
        submitted_at=sub,
    )


async def _seed_answer(
    db: AsyncSession,
    session_id: uuid.UUID,
    earned: float,
    max_pts: float,
    index: int = 0,
) -> SessionAnswer:
    ans = SessionAnswer(
        session_id=session_id,
        question_id=f"q{index}",
        question_index=index,
        submitted_answers=["A"],
        earned_points=earned,
        max_points=max_pts,
        is_correct=(earned == max_pts),
        answered_at=datetime(2026, 1, 1, 12, 30, 0),
    )
    db.add(ans)
    await db.flush()
    return ans


async def _seed_session_with_answers(
    db: AsyncSession,
    user_id: int,
    answers: list[tuple[float, float]],
    **session_kwargs,
) -> Session:
    s = _make_session(user_id, **session_kwargs)
    db.add(s)
    await db.flush()
    for i, (earned, max_pts) in enumerate(answers):
        await _seed_answer(db, s.session_id, earned, max_pts, index=i)
    return s


# ---------------------------------------------------------------------------
# Summary aggregate tests
# ---------------------------------------------------------------------------

async def test_summary_no_sessions_returns_zero_total(db):
    result = await ReportRepository.get_user_summary(db, user_id=99)
    assert result["total_attempts"] == 0
    assert result["average_score"] is None
    assert result["best_score"] is None
    assert result["total_time_spent"] is None
    assert result["most_recent_session"] is None


async def test_summary_single_completed_session_all_correct(db):
    server_now = datetime(2026, 1, 1, 12, 0, 0)
    submitted_at = datetime(2026, 1, 1, 12, 30, 0)
    s = await _seed_session_with_answers(
        db,
        user_id=1,
        answers=[(1.0, 1.0), (1.0, 1.0)],
        server_now=server_now,
        submitted_at=submitted_at,
    )

    result = await ReportRepository.get_user_summary(db, user_id=1)

    assert result["total_attempts"] == 1
    assert result["average_score"] == pytest.approx(1.0, abs=1e-4)
    assert result["best_score"] == pytest.approx(1.0, abs=1e-4)
    expected_seconds = (submitted_at - server_now).total_seconds()
    assert result["total_time_spent"] == pytest.approx(expected_seconds, abs=1e-3)
    assert result["most_recent_session"].session_id == s.session_id


async def test_summary_multiple_sessions_correct_average(db):
    # score ratios: 0.5, 0.75, 1.0 → average 0.75, best 1.0
    for earned, max_pts in [(1.0, 2.0), (3.0, 4.0), (1.0, 1.0)]:
        await _seed_session_with_answers(
            db,
            user_id=2,
            answers=[(earned, max_pts)],
            offset_seconds=0,
        )

    result = await ReportRepository.get_user_summary(db, user_id=2)

    assert result["total_attempts"] == 3
    assert result["average_score"] == pytest.approx(0.75, abs=1e-4)
    assert result["best_score"] == pytest.approx(1.0, abs=1e-4)


async def test_summary_session_without_answers_excluded_from_average(db):
    # One session with answers (score 1.0), one session with no answers (score NULL)
    await _seed_session_with_answers(db, user_id=3, answers=[(1.0, 1.0)])
    bare = _make_session(user_id=3, offset_seconds=60)
    db.add(bare)
    await db.flush()

    result = await ReportRepository.get_user_summary(db, user_id=3)

    assert result["total_attempts"] == 2
    # NULL score_ratio is excluded from AVG, so average is still 1.0
    assert result["average_score"] == pytest.approx(1.0, abs=1e-4)


async def test_summary_most_recent_attempt_is_latest_by_server_now(db):
    base = datetime(2026, 1, 1, 0, 0, 0)
    sessions = []
    for i in range(3):
        s = await _seed_session_with_answers(
            db,
            user_id=4,
            answers=[(1.0, 1.0)],
            server_now=base + timedelta(hours=i),
        )
        sessions.append(s)

    result = await ReportRepository.get_user_summary(db, user_id=4)

    assert result["most_recent_session"].session_id == sessions[2].session_id


async def test_summary_total_time_spent_excludes_sessions_without_submitted_at(db):
    server_now = datetime(2026, 1, 1, 12, 0, 0)
    submitted_at = datetime(2026, 1, 1, 12, 30, 0)
    # One completed session
    await _seed_session_with_answers(
        db,
        user_id=5,
        answers=[(1.0, 1.0)],
        server_now=server_now,
        submitted_at=submitted_at,
    )
    # One active session (no submitted_at)
    bare = _make_session(user_id=5, status=SessionStatus.ACTIVE, offset_seconds=3600)
    bare.submitted_at = None
    db.add(bare)
    await db.flush()

    result = await ReportRepository.get_user_summary(db, user_id=5)

    expected = (submitted_at - server_now).total_seconds()
    assert result["total_time_spent"] == pytest.approx(expected, abs=1e-3)


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------

async def test_list_attempts_default_page_returns_20_of_25(db):
    for i in range(25):
        s = _make_session(user_id=10, offset_seconds=i * 60)
        db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=10, filters=AttemptFilter()
    )

    assert total == 25
    assert len(items) == 20


async def test_list_attempts_page_2_returns_remaining_5(db):
    for i in range(25):
        s = _make_session(user_id=11, offset_seconds=i * 60)
        db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=11, filters=AttemptFilter(page=2, size=20)
    )

    assert total == 25
    assert len(items) == 5


async def test_list_attempts_size_clamp_enforced_via_service(db):
    for i in range(10):
        s = _make_session(user_id=12, offset_seconds=i * 60)
        db.add(s)
    await db.flush()

    # Service clamps size to 100
    response = await ReportService.list_attempts(
        db, user_id=12, filters=AttemptFilter(size=200)
    )

    assert response.size == 100
    assert len(response.items) <= 100


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------

async def test_list_attempts_filter_by_test_id(db):
    for test_id in [1, 2]:
        for _ in range(3):
            s = _make_session(user_id=20, test_id=test_id)
            db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=20, filters=AttemptFilter(test_id=1)
    )

    assert total == 3
    assert all(item["test_id"] == 1 for item in items)


async def test_list_attempts_filter_by_from_date(db):
    from datetime import date

    dates = [
        datetime(2026, 1, 1),
        datetime(2026, 2, 1),
        datetime(2026, 3, 1),
    ]
    for dt in dates:
        s = _make_session(user_id=21, server_now=dt)
        db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=21, filters=AttemptFilter(from_date=date(2026, 2, 1))
    )

    assert total == 2
    assert all(item["server_now"] >= datetime(2026, 2, 1) for item in items)


async def test_list_attempts_filter_by_to_date(db):
    from datetime import date

    dates = [
        datetime(2026, 1, 1),
        datetime(2026, 2, 1),
        datetime(2026, 3, 1),
    ]
    for dt in dates:
        s = _make_session(user_id=22, server_now=dt)
        db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=22, filters=AttemptFilter(to_date=date(2026, 1, 31))
    )

    assert total == 1
    assert items[0]["server_now"] < datetime(2026, 2, 1)


async def test_list_attempts_filter_by_status_completed(db):
    for status in [SessionStatus.COMPLETED, SessionStatus.ACTIVE, SessionStatus.EXPIRED]:
        s = _make_session(user_id=23, status=status)
        s.submitted_at = datetime(2026, 1, 1, 12, 30, 0) if status == SessionStatus.COMPLETED else None
        db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=23, filters=AttemptFilter(status=SessionStatus.COMPLETED)
    )

    assert total == 1
    assert all(item["status"] in ("COMPLETED", SessionStatus.COMPLETED) for item in items)


# ---------------------------------------------------------------------------
# Sort tests
# ---------------------------------------------------------------------------

async def test_list_attempts_sort_asc_server_now(db):
    base = datetime(2026, 1, 1)
    for i in range(5):
        s = _make_session(user_id=30, server_now=base + timedelta(days=i))
        db.add(s)
    await db.flush()

    items, _ = await ReportRepository.list_attempts(
        db, user_id=30, filters=AttemptFilter(sort="server_now:asc")
    )

    times = [item["server_now"] for item in items]
    assert times == sorted(times)


async def test_list_attempts_sort_desc_server_now(db):
    base = datetime(2026, 1, 1)
    for i in range(5):
        s = _make_session(user_id=31, server_now=base + timedelta(days=i))
        db.add(s)
    await db.flush()

    items, _ = await ReportRepository.list_attempts(
        db, user_id=31, filters=AttemptFilter(sort="server_now:desc")
    )

    times = [item["server_now"] for item in items]
    assert times == sorted(times, reverse=True)


async def test_list_attempts_sort_by_score_ratio_desc(db):
    for earned, max_pts in [(0.5, 1.0), (1.0, 1.0), (0.25, 1.0)]:
        await _seed_session_with_answers(
            db, user_id=32, answers=[(earned, max_pts)]
        )

    items, _ = await ReportRepository.list_attempts(
        db, user_id=32, filters=AttemptFilter(sort="score_ratio:desc")
    )

    ratios = [item["score_ratio"] for item in items if item["score_ratio"] is not None]
    assert ratios == sorted(ratios, reverse=True)


# ---------------------------------------------------------------------------
# User isolation tests
# ---------------------------------------------------------------------------

async def test_list_attempts_user_id_isolation(db):
    for user_id in [40, 41]:
        for _ in range(3):
            s = _make_session(user_id=user_id)
            db.add(s)
    await db.flush()

    items, total = await ReportRepository.list_attempts(
        db, user_id=40, filters=AttemptFilter()
    )

    assert total == 3
    assert all(item["user_id"] == 40 for item in items)


async def test_summary_user_id_isolation(db):
    for user_id in [50, 51]:
        await _seed_session_with_answers(db, user_id=user_id, answers=[(1.0, 1.0)])

    result_50 = await ReportRepository.get_user_summary(db, user_id=50)
    result_51 = await ReportRepository.get_user_summary(db, user_id=51)

    assert result_50["total_attempts"] == 1
    assert result_51["total_attempts"] == 1
    assert result_50["most_recent_session"].session_id != result_51["most_recent_session"].session_id


# ---------------------------------------------------------------------------
# Service validation tests
# ---------------------------------------------------------------------------

async def test_service_invalid_sort_raises_422(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await ReportService.list_attempts(
            db, user_id=1, filters=AttemptFilter(sort="badfield:up")
        )

    assert exc_info.value.status_code == 422


async def test_service_returns_zero_summary_for_unknown_user(db):
    response = await ReportService.get_user_summary(db, user_id=9999)

    assert response.total_attempts == 0
    assert response.average_score is None
    assert response.most_recent_attempt is None
