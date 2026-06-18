# src/db/session.py
import logging
import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ===== Base declarative class (this service's OWN schema — currently empty) =====
Base = declarative_base()


def _to_async(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url  # sqlite or already-async


# ===== Own engine: reporting's dedicated datastore (Alembic / alembic_version) =====
DATABASE_URL = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL
ASYNC_DATABASE_URL = _to_async(DATABASE_URL)

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ===== Read-only engine: test-management-service Postgres (eval_ai_dev) =====
# Report queries SELECT from sessions / quiz_answers / tests, tables owned by
# test-management-service's Alembic chain. This service NEVER writes on this
# engine and never emits DDL for these tables. See ADR 0001.
TMS_DATABASE_URL = os.getenv("TMS_DATABASE_URL") or settings.TMS_SQLALCHEMY_DATABASE_URL
TMS_ASYNC_DATABASE_URL = _to_async(TMS_DATABASE_URL)

tms_engine = create_async_engine(TMS_ASYNC_DATABASE_URL, echo=False, future=True)
TmsSessionLocal = sessionmaker(bind=tms_engine, class_=AsyncSession, expire_on_commit=False)


async def get_tms_db():
    async with TmsSessionLocal() as db:
        yield db


# ===== Initialize DB =====
async def init_db():
    """Verify both connections on startup.

    The own schema is owned by Alembic (`alembic upgrade head`, run by
    start.sh) — no create_all here. The TMS engine is read-only; its schema is
    owned by test-management-service's Alembic chain.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Own DB connected successfully.")
    except OperationalError:
        logger.error("❌ Own DB connection failed!", exc_info=True)
    try:
        async with tms_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ TMS (read-only) DB connected successfully.")
    except OperationalError:
        logger.error("❌ TMS (read-only) DB connection failed!", exc_info=True)
