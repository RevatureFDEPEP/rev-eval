# src/db/session.py
import logging
import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import settings

# ===== Base declarative class =====
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
engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)

# ===== Async Session Factory =====
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


# ===== Dependency for FastAPI =====
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ===== Initialize DB =====
async def init_db():
    """
    Import all models, create tables (async), and test connection.
    Call this on app startup.
    """
    try:
        # Import all models here so they are registered with Base

        # Create tables in async context
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Test async connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Async DB connected successfully and tables are ready.")
    except OperationalError as e:
        logger.error("Async DB connection failed: %s", e, exc_info=True)
