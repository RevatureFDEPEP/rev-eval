# src/db/session.py
import logging
import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import settings

# ===== Base declarative class =====
# Reporting owns no tables today; Base exists for read-only model mappings
# (W4-F1) and any future reporting-owned tables.
Base = declarative_base()

# ===== Database URL =====
DATABASE_URL = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL

# Convert to async URL for asyncpg
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgresql+psycopg2://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
else:
    ASYNC_DATABASE_URL = DATABASE_URL  # for sqlite or other DBs

logger = logging.getLogger(__name__)

# ===== Async Engine =====
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)

# ===== Async Session Factory =====
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


# ===== Dependency for FastAPI =====
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ===== Connection check (read-only — never creates tables) =====
async def verify_db_connection() -> None:
    """Verify the shared database is reachable on startup.

    Unlike the writer services, reporting NEVER calls ``create_all``: it reads
    tables owned by test-management-service. A failure here is logged, not
    raised, so the service still starts (and its /health stays green) while the
    database finishes coming up.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Async DB connection verified (read-only).")
    except OperationalError as e:
        logger.error("Async DB connection failed: %s", e, exc_info=True)
