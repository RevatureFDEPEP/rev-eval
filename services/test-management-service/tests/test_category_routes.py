"""Route-level tests for the Category endpoints.

Covers the trainer-only write guard (PR #84 follow-up fix #4) and basic CRUD
reachability without any network: an in-memory SQLite engine is injected via
`get_db`, and the gateway-injected identity is faked by overriding
`get_current_user_from_headers` (the REAL `get_current_trainer` still runs, so
the 403 path exercises the actual guard).
"""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.session import Base, get_db
from src.utils.dependencies import get_current_user_from_headers
from src.v1.routes.category_route import router as category_router


@pytest_asyncio.fixture
async def session_factory():
    # Import all models so create_all builds the full schema (FKs included).
    from src.models.category import Category  # noqa: F401
    from src.models.category_skill import CategorySkill  # noqa: F401
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


def _build_client(session_factory, role: str | None):
    app = FastAPI()
    app.include_router(category_router, prefix="/v1/api")

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_user():
        return {"id": 1, "email": "u@x.io", "role": role}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_from_headers] = _override_user
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_create_requires_trainer_rejects_participant(session_factory):
    async with _build_client(session_factory, role="PARTICIPANT") as client:
        resp = await client.post("/v1/api/categories/", json={"name": "Backend"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_allows_trainer(session_factory):
    async with _build_client(session_factory, role="TRAINER") as client:
        resp = await client.post("/v1/api/categories/", json={"name": "Backend"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Backend"
    assert body["id"]


@pytest.mark.asyncio
async def test_list_is_open_to_any_authenticated_user(session_factory):
    # Seed one category as a trainer...
    async with _build_client(session_factory, role="TRAINER") as client:
        await client.post("/v1/api/categories/", json={"name": "Backend"})
    # ...then read it back as a participant (GET is not guarded).
    async with _build_client(session_factory, role="PARTICIPANT") as client:
        resp = await client.get("/v1/api/categories/")
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["Backend"]


@pytest.mark.asyncio
async def test_update_and_delete_require_trainer(session_factory):
    async with _build_client(session_factory, role="TRAINER") as client:
        created = (await client.post("/v1/api/categories/", json={"name": "Backend"})).json()
    cid = created["id"]

    async with _build_client(session_factory, role="PARTICIPANT") as client:
        upd = await client.put(f"/v1/api/categories/{cid}/", json={"name": "X"})
        dele = await client.delete(f"/v1/api/categories/{cid}/")
    assert upd.status_code == 403
    assert dele.status_code == 403
