# src/db/session.py
import logging
import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config.settings import settings

logger = logging.getLogger(__name__)

# ===== Base declarative class =====
Base = declarative_base()

# ===== Database URL =====
DATABASE_URL = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL

# Convert to async URL for asyncpg
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgresql+psycopg2://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL  # for sqlite or other DBs

# ===== Async Engine =====
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    future=True
)

# ===== Async Session Factory =====
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ===== Dependency for FastAPI =====
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# ===== Initialize DB =====
async def init_db():
    """
    Register all models and test the connection. Call this on app startup.

    Schema creation/evolution is owned by Alembic (alembic upgrade head,
    run by start.sh before the app boots) — create_all was removed when
    migrations were introduced so a broken migration can't be papered over.
    """
    try:
        # Import all models here so they are registered with Base.metadata
        # and relationship strings resolve. Keep in sync with alembic/env.py.
        from src.models.answer import Answer  # noqa: F401
        from src.models.category import Category  # noqa: F401
        from src.models.idempotency_key import IdempotencyKey  # noqa: F401
        from src.models.session import Session  # noqa: F401
        from src.models.skill import Skill  # noqa: F401
        from src.models.test import Test  # noqa: F401
        from src.models.test_skill import TestSkill  # noqa: F401
        from src.models.test_submission import TestSubmission  # noqa: F401

        # Test async connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Async DB connected successfully.")
    except OperationalError:
        logger.error("Async DB connection failed!", exc_info=True)
