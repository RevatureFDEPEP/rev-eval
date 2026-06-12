"""Route-level tests for POST /v1/api/sessions.

No network: an in-memory SQLite engine is injected via `get_db`, the
gateway-injected identity is faked by overriding `get_current_user_from_headers`,
and the httpx call to question-management-service is replaced with a fake client
so the $sample fan-out is mocked. (Real pg+mongo happy-path lives in W3-F5.)
"""
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.services.session_service as session_service_mod
from src.db.session import Base, get_db
from src.models.session import QuizSession
from src.models.test import Test, TestType
from src.utils.dependencies import get_current_user_from_headers
from src.v1.routes.session_route import router as session_router

# A two-question sample payload mimicking question-management-service's response.
# Note: that service serializes by alias, so the id key is "_id" (not "id").
_SAMPLE_PAYLOAD = [
    {"_id": "q1", "type": "mcq", "question_text": "What is 2+2?",
     "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}],
     "created_at": "2026-06-11T00:00:00", "updated_at": "2026-06-11T00:00:00"},
    {"_id": "q2", "type": "true_false", "question_text": "The sky is blue.",
     "created_at": "2026-06-11T00:00:00", "updated_at": "2026-06-11T00:00:00"},
]


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    async def get(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self._response


@pytest_asyncio.fixture
async def session_factory():
    from src.models.category import Category  # noqa: F401
    from src.models.category_skill import CategorySkill  # noqa: F401
    from src.models.session import QuizSession  # noqa: F401
    from src.models.skill import Skill  # noqa: F401
    from src.models.test import Test  # noqa: F401
    from src.models.test_skill import TestSkill  # noqa: F401
    from src.models.test_submission import TestSubmission  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _seed_test(session_factory, *, duration, number_of_questions=2) -> int:
    async with session_factory() as session:
        test = Test(
            name="Sample Quiz",
            test_type=TestType.QUIZ,
            duration=duration,
            number_of_questions=number_of_questions,
            active=True,
        )
        session.add(test)
        await session.commit()
        await session.refresh(test)
        return test.id


def _build_client(session_factory):
    app = FastAPI()
    app.include_router(session_router, prefix="/v1/api")

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_user():
        return {"id": 42, "email": "p@x.io", "role": "PARTICIPANT"}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_from_headers] = _override_user
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_create_session_happy_path(session_factory, monkeypatch):
    test_id = await _seed_test(session_factory, duration=timedelta(minutes=30))
    fake = _FakeClient(_FakeResponse(200, _SAMPLE_PAYLOAD))
    monkeypatch.setattr(session_service_mod, "get_http_client", lambda: fake)

    async with _build_client(session_factory) as client:
        resp = await client.post("/v1/api/sessions/", json={"test_id": test_id})

    assert resp.status_code == 201
    body = resp.json()
    # Sequential-reveal contract: current question only + progress counters.
    assert set(body) >= {
        "session_id", "session_token", "server_now", "expires_at",
        "current_index", "total_questions", "question",
    }
    # SanitizedQuestion maps the Mongo "_id" alias onto "id" and strips the key.
    assert body["question"]["id"] == "q1"
    assert "correct_answers" not in body["question"]
    assert body["current_index"] == 0
    assert body["total_questions"] == 2
    assert len(body["session_token"]) == 64  # secrets.token_hex(32)

    # expires_at = server_now + test.duration (30 min)
    server_now = datetime.fromisoformat(body["server_now"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert (expires_at - server_now) == timedelta(minutes=30)

    # $sample was asked for exactly number_of_questions
    assert fake.calls[0]["params"] == {"limit": 2}

    # Row persisted with the snapshotted ordered question IDs
    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == body["session_id"])
        )).scalars().first()
        assert row is not None
        assert row.user_id == 42
        assert row.question_ids == ["q1", "q2"]
        assert row.current_index == 0


@pytest.mark.asyncio
async def test_create_session_unknown_test_returns_404(session_factory, monkeypatch):
    fake = _FakeClient(_FakeResponse(200, _SAMPLE_PAYLOAD))
    monkeypatch.setattr(session_service_mod, "get_http_client", lambda: fake)

    async with _build_client(session_factory) as client:
        resp = await client.post("/v1/api/sessions/", json={"test_id": 9999})

    assert resp.status_code == 404
    # Test lookup fails before any question-mgmt call.
    assert fake.calls == []


@pytest.mark.asyncio
async def test_create_session_null_duration_defaults_60min(session_factory, monkeypatch):
    test_id = await _seed_test(session_factory, duration=None)
    fake = _FakeClient(_FakeResponse(200, _SAMPLE_PAYLOAD))
    monkeypatch.setattr(session_service_mod, "get_http_client", lambda: fake)

    async with _build_client(session_factory) as client:
        resp = await client.post("/v1/api/sessions/", json={"test_id": test_id})

    assert resp.status_code == 201
    body = resp.json()
    server_now = datetime.fromisoformat(body["server_now"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert (expires_at - server_now) == timedelta(minutes=60)
