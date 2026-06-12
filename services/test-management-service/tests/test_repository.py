"""
Repository tests for test-management-service using in-memory SQLite.

Creates a dedicated async engine per test module, isolated from the
production asyncpg engine. Uses aiosqlite as the async SQLite driver.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.db.session import Base
from src.models.test import TestType  # noqa: F401  # registers model with Base metadata
from src.models.test_submission import TestSubmission  # noqa: F401  # registers relationship with Base metadata
from src.models.test_skill import TestSkill  # noqa: F401  # registers relationship with Base metadata
from src.models.skill import Skill  # noqa: F401  # registers skills table with Base metadata
from src.repositories.test_repository import TestRepository
from src.schemas.test_schema import TestCreate, TestUpdate


@pytest_asyncio.fixture(scope="module")
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


async def test_create_and_get_by_id(async_db):
    created = await TestRepository.create(
        async_db,
        TestCreate(name="Python Basics", test_type="QUIZ", created_by_id=1),
    )
    assert created.id is not None
    assert created.name == "Python Basics"

    fetched = await TestRepository.get_by_id(async_db, created.id)
    assert fetched is not None
    assert fetched.name == "Python Basics"
    assert fetched.test_type == TestType.QUIZ


async def test_list_all_returns_created_tests(async_db):
    await TestRepository.create(
        async_db,
        TestCreate(name="React Fundamentals", test_type="QUIZ", created_by_id=2),
    )
    tests = await TestRepository.list_all(async_db)
    names = [t.name for t in tests]
    assert "React Fundamentals" in names


async def test_update_test_name(async_db):
    created = await TestRepository.create(
        async_db,
        TestCreate(name="Old Name", test_type="INTERVIEW", created_by_id=1),
    )
    updated = await TestRepository.update(
        async_db, created, TestUpdate(name="New Name")
    )
    assert updated.name == "New Name"
    assert updated.test_type == TestType.INTERVIEW


async def test_delete_removes_record(async_db):
    created = await TestRepository.create(
        async_db,
        TestCreate(name="To Be Deleted", test_type="QUIZ", created_by_id=99),
    )
    deleted_id = created.id
    await TestRepository.delete(async_db, created)

    fetched = await TestRepository.get_by_id(async_db, deleted_id)
    assert fetched is None
