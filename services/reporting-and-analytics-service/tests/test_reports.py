"""Route-level tests for the candidate reporting endpoints (W4-F1).

No network: an in-memory SQLite engine holding the read-only TMS tables is
injected via `get_tms_db`. A seeded dataset exercises aggregate correctness
(SUBMITTED-only, percentages), most-recent selection, pagination meta, filters,
sort whitelist + 422s, and null-score-until-SUBMITTED.
"""
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.session import get_tms_db
from src.models.tms_readonly import SessionStatus, TmsAnswer, TmsBase, TmsSession, TmsTest
from src.v1.routes.reports_route import router as reports_router

T0 = datetime(2026, 6, 17, 9, 0, 0)


@pytest_asyncio.fixture
async def tms_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(TmsBase.metadata.create_all)
    yield sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _seed(factory):
    async with factory() as db:
        db.add_all([TmsTest(id=1, name="Python Basics"), TmsTest(id=2, name="SQL Joins")])
        # user 4 attempt 1: test 1, SUBMITTED, 600s, scores 1.0+0.5 -> 75%
        db.add(TmsSession(
            session_id="s1", test_id=1, user_id=4, status=SessionStatus.SUBMITTED,
            started_at=T0, expires_at=T0 + timedelta(minutes=45),
            submitted_at=T0 + timedelta(seconds=600), created_at=T0,
        ))
        # user 4 attempt 2: test 2, SUBMITTED later, 300s, scores 1.0+1.0 -> 100%
        db.add(TmsSession(
            session_id="s2", test_id=2, user_id=4, status=SessionStatus.SUBMITTED,
            started_at=T0 + timedelta(hours=1), expires_at=T0 + timedelta(hours=2),
            submitted_at=T0 + timedelta(hours=1, seconds=300),
            created_at=T0 + timedelta(hours=1),
        ))
        # user 4 ACTIVE attempt with a partial answer — must NOT count in summary
        # and must expose score=null in the attempts list.
        db.add(TmsSession(
            session_id="s4", test_id=1, user_id=4, status=SessionStatus.ACTIVE,
            started_at=T0 + timedelta(hours=2), expires_at=T0 + timedelta(hours=3),
            submitted_at=None, created_at=T0 + timedelta(hours=2),
        ))
        # user 5: unrelated, isolation check
        db.add(TmsSession(
            session_id="s3", test_id=1, user_id=5, status=SessionStatus.SUBMITTED,
            started_at=T0, expires_at=T0 + timedelta(minutes=45),
            submitted_at=T0 + timedelta(seconds=120), created_at=T0,
        ))
        db.add_all([
            TmsAnswer(session_id="s1", question_id="q1", question_index=0, score=1.0, is_correct=True),
            TmsAnswer(session_id="s1", question_id="q2", question_index=1, score=0.5, is_correct=False),
            TmsAnswer(session_id="s2", question_id="q3", question_index=0, score=1.0, is_correct=True),
            TmsAnswer(session_id="s2", question_id="q4", question_index=1, score=1.0, is_correct=True),
            TmsAnswer(session_id="s4", question_id="q1", question_index=0, score=1.0, is_correct=True),
            TmsAnswer(session_id="s3", question_id="q1", question_index=0, score=0.0, is_correct=False),
        ])
        await db.commit()


def _app(factory):
    app = FastAPI()
    app.include_router(reports_router, prefix="/v1/api")

    async def _get_tms_db():
        async with factory() as db:
            yield db

    app.dependency_overrides[get_tms_db] = _get_tms_db
    return app


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_user_summary_aggregates_submitted_only(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4")
    assert r.status_code == 200
    b = r.json()
    assert b["user_id"] == 4
    assert b["total_attempts"] == 2  # ACTIVE s4 excluded
    assert b["avg_score"] == pytest.approx(87.5)  # mean of 75 and 100
    assert b["best_score"] == pytest.approx(100.0)
    assert b["total_time_seconds"] == pytest.approx(900.0)  # 600 + 300
    assert b["most_recent"]["session_id"] == "s2"
    assert b["most_recent"]["test_name"] == "SQL Joins"
    assert b["most_recent"]["score"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_summary_no_attempts_zeroed(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/77")
    assert r.status_code == 200
    b = r.json()
    assert b["total_attempts"] == 0
    assert b["avg_score"] is None
    assert b["best_score"] is None
    assert b["total_time_seconds"] is None
    assert b["most_recent"] is None


@pytest.mark.asyncio
async def test_attempts_pagination_meta_and_default_sort(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?page=1&size=2")
    assert r.status_code == 200
    b = r.json()
    assert b["total"] == 3  # s1, s2, s4 (all user-4 sessions)
    assert b["page"] == 1 and b["size"] == 2
    assert len(b["items"]) == 2
    # submitted_at:desc nullslast -> s2 first (latest submitted), then s1
    assert [i["session_id"] for i in b["items"]] == ["s2", "s1"]
    assert b["items"][0]["score"] == pytest.approx(100.0)
    assert b["items"][0]["duration_seconds"] == pytest.approx(300.0)
    assert b["items"][0]["questions_answered"] == 2


@pytest.mark.asyncio
async def test_active_attempt_score_is_null(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?status=ACTIVE")
    assert r.status_code == 200
    b = r.json()
    assert b["total"] == 1
    item = b["items"][0]
    assert item["session_id"] == "s4"
    assert item["score"] is None  # partial running average must not leak
    assert item["submitted_at"] is None
    assert item["duration_seconds"] is None
    assert item["questions_answered"] == 1


@pytest.mark.asyncio
async def test_attempts_filter_by_test(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?test_id=2")
    b = r.json()
    assert b["total"] == 1
    assert b["items"][0]["session_id"] == "s2"


@pytest.mark.asyncio
async def test_attempts_sort_score_desc(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?sort=score:desc")
    ids = [i["session_id"] for i in r.json()["items"]]
    # 100 (s2), 75 (s1), then ACTIVE s4 (null) last
    assert ids == ["s2", "s1", "s4"]


@pytest.mark.asyncio
async def test_attempts_date_filter_on_start(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        # s1 starts 09:00 on 2026-06-17; s2/s4 start same day too -> all 3 match
        r = await c.get("/v1/api/reports/user/4/attempts?from=2026-06-17&to=2026-06-17")
    assert r.json()["total"] == 3


@pytest.mark.asyncio
async def test_invalid_sort_422(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?sort=bogus")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_size_over_max_422(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/4/attempts?size=500")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_user_isolation(tms_factory):
    await _seed(tms_factory)
    async with _client(_app(tms_factory)) as c:
        r = await c.get("/v1/api/reports/user/5")
    b = r.json()
    assert b["total_attempts"] == 1
    assert b["most_recent"]["session_id"] == "s3"
