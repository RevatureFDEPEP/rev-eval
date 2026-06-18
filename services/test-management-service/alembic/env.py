"""
Alembic environment for test-management-service (async SQLAlchemy / asyncpg).

The database URL is read from the DATABASE_URL environment variable at runtime,
falling back to the settings SQLALCHEMY_DATABASE_URL if the env var is absent.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Make src importable when running alembic from the service root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import Base so all models register their metadata
import src.models.session  # noqa: F401

# Ensure all models are imported so their tables appear in Base.metadata
import src.models.skill  # noqa: F401
import src.models.test  # noqa: F401
import src.models.test_skill  # noqa: F401
import src.models.test_submission  # noqa: F401
from src.config.settings import settings  # noqa: E402
from src.db.session import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from the environment so alembic never uses the
# placeholder from alembic.ini.
def _get_url() -> str:
    url = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
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


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
