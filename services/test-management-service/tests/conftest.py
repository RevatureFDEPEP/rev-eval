import os

# Satisfy pydantic-settings before any src.* import
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpassword")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
# Override DATABASE_URL so session.py picks up SQLite instead of Postgres
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.db.session import Base
# Import all models to register table metadata


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
