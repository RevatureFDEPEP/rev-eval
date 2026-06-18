"""
Shared fixtures for reporting-and-analytics-service tests.

Provides an in-memory SQLite database (shared across connections via StaticPool),
a seeded dataset with known aggregate values, an AsyncSession, and a FastAPI
TestClient with get_db overridden to use the test database.
"""
from datetime import datetime

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.db.session import Base, get_db
from src.models.session_mirror import AttemptStatus, SessionMirror

# User under test plus an unrelated user to prove per-user isolation.
USER_ID = 100
OTHER_USER_ID = 200

# Known dataset for USER_ID:
#   scores       -> 80, 90, 50, 70   (avg 72.5, best 90)
#   time_spent   -> 300, 200, 100, 150 (sum 750)
#   most recent  -> a4 (created 2026-06-15)
SEED_ATTEMPTS = [
    dict(session_id="a1", user_id=USER_ID, test_id="t1",
         status=AttemptStatus.COMPLETED, score=80.0, time_spent_seconds=300,
         created_at=datetime(2026, 6, 1, 9, 0)),
    dict(session_id="a2", user_id=USER_ID, test_id="t1",
         status=AttemptStatus.SUBMITTED, score=90.0, time_spent_seconds=200,
         created_at=datetime(2026, 6, 5, 9, 0)),
    dict(session_id="a3", user_id=USER_ID, test_id="t2",
         status=AttemptStatus.ABANDONED, score=50.0, time_spent_seconds=100,
         created_at=datetime(2026, 6, 10, 9, 0)),
    dict(session_id="a4", user_id=USER_ID, test_id="t2",
         status=AttemptStatus.COMPLETED, score=70.0, time_spent_seconds=150,
         created_at=datetime(2026, 6, 15, 9, 0)),
    dict(session_id="b1", user_id=OTHER_USER_ID, test_id="t1",
         status=AttemptStatus.COMPLETED, score=10.0, time_spent_seconds=999,
         created_at=datetime(2026, 6, 2, 9, 0)),
]


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded(session_factory):
    async with session_factory() as session:
        for attrs in SEED_ATTEMPTS:
            session.add(SessionMirror(**attrs))
        await session.commit()
    return SEED_ATTEMPTS


@pytest_asyncio.fixture
async def db(session_factory, seeded):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(session_factory, seeded):
    from main import app

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
