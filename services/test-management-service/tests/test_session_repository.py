"""
Repository tests for Session using in-memory SQLite.

Follows the same pattern as test_repository.py: a module-scoped async SQLite
engine; all models imported so their tables are created via Base.metadata.
"""
import uuid
from datetime import datetime, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.db.session import Base
from src.models.session import Session, SessionStatus  # noqa: F401 — registers table
from src.models.skill import Skill  # noqa: F401 — registers table
from src.models.test import Test  # noqa: F401 — registers table
from src.models.test_skill import TestSkill  # noqa: F401 — registers table
from src.models.test_submission import TestSubmission  # noqa: F401 — registers table
from src.repositories.session_repository import SessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.test_schema import TestCreate


@pytest_asyncio.fixture(scope="module")
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def sample_test(async_db):
    """Create a Test row so the sessions FK can be satisfied."""
    test = await TestRepository.create(
        async_db,
        TestCreate(
            name="Session Test",
            test_type="QUIZ",
            created_by_id=1,
            duration_seconds=3600,
            number_of_questions=10,
        ),
    )
    return test


async def test_create_session_and_get_by_id(async_db, sample_test):
    server_now = datetime(2026, 6, 18, 10, 0, 0)
    expires_at = server_now + timedelta(hours=1)
    session_id = str(uuid.uuid4())

    created = await SessionRepository.create(
        async_db,
        session_id=session_id,
        test_id=sample_test.id,
        user_id=7,
        session_token="abc" * 20,
        server_now=server_now,
        expires_at=expires_at,
    )
    assert created.session_id == session_id
    assert created.test_id == sample_test.id
    assert created.user_id == 7
    assert created.status == SessionStatus.ACTIVE
    assert created.current_index == 0

    fetched = await SessionRepository.get_by_id(async_db, session_id)
    assert fetched is not None
    assert fetched.session_id == session_id
    assert fetched.expires_at == expires_at


async def test_list_by_user_returns_correct_sessions(async_db, sample_test):
    sid = str(uuid.uuid4())
    await SessionRepository.create(
        async_db,
        session_id=sid,
        test_id=sample_test.id,
        user_id=42,
        session_token="tok" + sid,
        server_now=datetime(2026, 6, 18, 9, 0),
        expires_at=datetime(2026, 6, 18, 11, 0),
    )
    results = await SessionRepository.list_by_user(async_db, 42)
    assert any(s.session_id == sid for s in results)


async def test_list_by_test_returns_correct_sessions(async_db, sample_test):
    sid = str(uuid.uuid4())
    await SessionRepository.create(
        async_db,
        session_id=sid,
        test_id=sample_test.id,
        user_id=99,
        session_token="test" + sid,
        server_now=datetime(2026, 6, 18, 8, 0),
        expires_at=datetime(2026, 6, 18, 10, 0),
    )
    results = await SessionRepository.list_by_test(async_db, sample_test.id)
    assert any(s.session_id == sid for s in results)


async def test_get_by_id_returns_none_for_missing_session(async_db):
    result = await SessionRepository.get_by_id(async_db, str(uuid.uuid4()))
    assert result is None
