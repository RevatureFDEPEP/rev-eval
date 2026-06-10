import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from src.db.session import Base  # noqa: E402

# Import all models so they register on Base.metadata before create_all
from src.models.quiz_session import QuizSession  # noqa: E402, F401
from src.models.skill import Skill  # noqa: E402, F401
from src.models.test import Test  # noqa: E402, F401
from src.models.test_skill import TestSkill  # noqa: E402, F401
from src.models.test_submission import TestSubmission  # noqa: E402, F401


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Hermetic in-memory SQLite AsyncSession — one fresh schema per test."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()
