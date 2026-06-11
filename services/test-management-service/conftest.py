import os

# Must be set before any service module is imported (pydantic-settings reads env on class load).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Hermetic async session backed by in-memory SQLite.

    Builds a test-local engine (not the module-global one bound to DATABASE_URL).
    StaticPool + a single shared connection keeps the schema alive for the
    fixture lifetime — a fresh :memory: DB disappears when its connection closes.
    """
    from src.db.session import Base
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

    session_factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
