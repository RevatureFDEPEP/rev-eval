import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import settings
from src.db.session import Base

# Import all models so they register on Base.metadata for autogenerate.
from src.models.category import Category  # noqa: F401
from src.models.category_skill import CategorySkill  # noqa: F401
from src.models.session import QuizSession  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test import Test  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Configure Python logging from the alembic.ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL, coerced to an async driver.

    Mirrors src/db/session.py: prefer an explicit DATABASE_URL, else build from
    the DB_* settings (how the service is actually configured in docker-compose,
    where DATABASE_URL is unset). Without this fallback alembic defaulted to
    localhost and could not reach the `postgres` container at boot.
    """
    url = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an async engine."""
    engine = create_async_engine(get_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
