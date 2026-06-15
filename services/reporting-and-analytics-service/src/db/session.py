import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from src.config.settings import settings

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL

if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgresql+psycopg2://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


async def init_db():
    try:
        from src.models.reporting_models import Test, TestSubmission, QuizSession  # noqa: F401

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Reporting service DB connected.")
    except OperationalError as e:  # pragma: no cover
        print(f"❌ DB connection failed: {e}")
