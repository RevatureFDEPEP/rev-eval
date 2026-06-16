"""Route-level tests for PATCH /v1/api/sessions/{id}/draft (W3-F4 autosave).

In-memory SQLite via `get_db`, faked gateway identity. Autosave is a
last-write-wins snapshot that must NOT advance `current_index` or change
`status`; terminal/expired sessions reject 409, other users 403, missing 404.
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

from src.db.session import Base, get_db
from src.models.session import QuizSession, SessionStatus
from src.utils.dependencies import get_current_user_from_headers
from src.v1.routes.session_route import router as session_router

_USER_ID = 42


@pytest_asyncio.fixture
async def session_factory():
    from src.models.answer import QuizAnswer  # noqa: F401
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


async def _seed_session(
    session_factory,
    *,
    question_ids,
    current_index=0,
    status=SessionStatus.ACTIVE,
    expires_in=timedelta(minutes=30),
    user_id=_USER_ID,
    session_id="sess-1",
) -> str:
    now = datetime.utcnow()
    async with session_factory() as session:
        session.add(
            QuizSession(
                session_id=session_id,
                test_id=1,
                user_id=user_id,
                session_token="t" * 64,
                server_now=now,
                expires_at=now + expires_in,
                status=status,
                current_index=current_index,
                question_ids=question_ids,
            )
        )
        await session.commit()
    return session_id


def _build_client(session_factory):
    app = FastAPI()
    app.include_router(session_router, prefix="/v1/api")

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_user():
        return {"id": _USER_ID, "email": "p@x.io", "role": "PARTICIPANT"}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_from_headers] = _override_user
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_draft_persists_without_advancing(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq", "q-tf"], current_index=1
    )
    answers = {"q-mcq": [2], "q-tf": [1]}
    async with _build_client(session_factory) as client:
        resp = await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": answers}
        )
    assert resp.status_code == 200
    body = resp.json()
    # Echoes the UNCHANGED state so the client can confirm non-mutation.
    assert body["session_id"] == sid
    assert body["status"] == "ACTIVE"
    assert body["current_index"] == 1
    assert body["saved_at"] is not None

    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.draft_answers == answers
        assert row.current_index == 1       # NOT advanced
        assert row.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_draft_is_last_write_wins(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-mcq"])
    async with _build_client(session_factory) as client:
        await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": {"q-mcq": [1]}}
        )
        resp = await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": {"q-mcq": [2, 3]}}
        )
    assert resp.status_code == 200
    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.draft_answers == {"q-mcq": [2, 3]}  # latest wins


@pytest.mark.asyncio
async def test_draft_on_submitted_session_returns_409(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], status=SessionStatus.SUBMITTED
    )
    async with _build_client(session_factory) as client:
        resp = await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": {"q-mcq": [1]}}
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_draft_on_expired_session_finalizes_and_409(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], expires_in=timedelta(minutes=-1)
    )
    async with _build_client(session_factory) as client:
        resp = await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": {"q-mcq": [1]}}
        )
    assert resp.status_code == 409
    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.status == SessionStatus.EXPIRED


@pytest.mark.asyncio
async def test_draft_other_users_session_returns_403(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], user_id=999
    )
    async with _build_client(session_factory) as client:
        resp = await client.patch(
            f"/v1/api/sessions/{sid}/draft", json={"answers": {"q-mcq": [1]}}
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_draft_missing_session_returns_404(session_factory):
    async with _build_client(session_factory) as client:
        resp = await client.patch(
            "/v1/api/sessions/nope/draft", json={"answers": {"q-mcq": [1]}}
        )
    assert resp.status_code == 404
