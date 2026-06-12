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
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)

# ===== Async Session Factory =====
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ===== Dependency for FastAPI =====
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

# ===== Read-only engine: test-management-service Postgres (eval_ai_dev) =====
# Report queries SELECT from sessions/answers/tests, tables owned by the TMS
# Alembic chain. This service never writes on this engine and never emits DDL
# for these tables. See docs/adr/0001-reporting-cross-service-data-access.md.
TMS_DATABASE_URL = os.getenv("TMS_DATABASE_URL") or settings.TMS_SQLALCHEMY_DATABASE_URL

if TMS_DATABASE_URL.startswith("postgresql://"):
    TMS_ASYNC_DATABASE_URL = TMS_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif TMS_DATABASE_URL.startswith("postgresql+psycopg2://"):
    TMS_ASYNC_DATABASE_URL = TMS_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
else:
    TMS_ASYNC_DATABASE_URL = TMS_DATABASE_URL  # for sqlite or other DBs

tms_engine = create_async_engine(TMS_ASYNC_DATABASE_URL, echo=False, future=True)

TmsSessionLocal = sessionmaker(bind=tms_engine, class_=AsyncSession, expire_on_commit=False)

async def get_tms_db():
    async with TmsSessionLocal() as db:
        yield db

# ===== Initialize DB =====
async def init_db():
    """
    Test both connections on app startup.

    Schema creation/evolution for the reporting datastore is owned by Alembic
    (`alembic upgrade head`, run by start.sh before the app boots) — there is
    no create_all here. Model imports go here once reporting-owned models
    exist, keeping them in sync with alembic/env.py so relationship strings
    resolve. The TMS engine is read-only; its schema is owned by
    test-management-service's Alembic chain.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Async DB connected successfully.")
    except OperationalError:
        logger.error("Async DB connection failed!", exc_info=True)
    try:
        async with tms_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("TMS (read-only) DB connected successfully.")
    except OperationalError:
        logger.error("TMS (read-only) DB connection failed!", exc_info=True)
