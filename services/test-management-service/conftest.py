"""Test bootstrap for test-management-service.

`src.config.settings.Settings()` runs at import and requires DB_* plus
ALLOW_ORIGINS / SERVICE_NAME / PORT / SERVICE_HOSTNAME. Set hermetic defaults
here (imported before test collection) so importing the service modules never
opens a real database connection — the async engine is created lazily.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "eval_ai_dev")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """A hermetic async SQLAlchemy session backed by in-memory SQLite.

    Builds a *test-local* engine (NOT the module-global ``src.db.session.engine``,
    which is bound to the env DATABASE_URL at import time). The schema is created
    from ``Base.metadata`` after importing every model — the same import list
    ``init_db()`` uses — so all tables and relationships are registered. No
    Postgres, no Alembic, no external services: tests stay fast and hermetic.

    ``StaticPool`` + a single shared in-memory connection keeps the schema alive
    for the lifetime of the fixture (a fresh ``:memory:`` DB otherwise vanishes
    when its connection is returned to the pool).
    """
    from src.db.session import Base

    # Register all models so Base.metadata is fully populated before create_all.
    # Mirror the import list in src/db/session.py:init_db.
    from src.models.category import Category  # noqa: F401
    from src.models.session import Session  # noqa: F401
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
