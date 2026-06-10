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

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run tests/integration/ against real Postgres/Mongo containers "
        "(docker compose up -d --wait postgres mongo question-management-service)",
    )


def pytest_configure(config):
    """Wire env for the integration suite before any ``src`` module is imported.

    ``src.config.settings.Settings()`` and the ``src.db.session`` engine bind
    their env at import time, and test modules import them during collection —
    so the integration URLs must be in the environment before collection
    starts. ``IT_*`` variables override the localhost compose-port defaults.
    """
    if config.getoption("--integration"):
        it_db_url = os.environ.setdefault(
            "IT_DATABASE_URL",
            "postgresql+asyncpg://root:root@localhost:5432/eval_ai_itest",
        )
        os.environ["DATABASE_URL"] = it_db_url
        os.environ["QUESTION_SERVICE_URL"] = os.environ.setdefault(
            "IT_QUESTION_SERVICE_URL", "http://localhost:8003"
        )


def pytest_collection_modifyitems(config, items):
    """Mark everything under tests/integration/ and gate it on --integration.

    Plain ``pytest`` runs (unit CI step, the Dockerfile ``test`` stage — no
    databases available there) skip the integration suite untouched.
    """
    run_integration = config.getoption("--integration")
    skip = pytest.mark.skip(
        reason="needs real containers — pass --integration "
        "(see tests/integration/conftest.py for the compose command)"
    )
    for item in items:
        if "tests/integration/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(pytest.mark.integration)
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip)


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
    from src.models.answer import Answer  # noqa: F401
    from src.models.category import Category  # noqa: F401
    from src.models.idempotency_key import IdempotencyKey  # noqa: F401
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
