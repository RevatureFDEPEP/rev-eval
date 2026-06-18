"""Async Alembic environment for test-management-service.

This file is intentionally aligned with src/db/session.py:
  * The DB URL precedence is identical — DATABASE_URL env var first, then the
    service settings (SQLALCHEMY_DATABASE_URL).
  * The sync driver is normalized to the async driver (asyncpg for Postgres),
    so migrations run inside an async engine via connection.run_sync(...).

It also imports the service Base and every model module before Alembic reads
``target_metadata`` — without those imports autogenerate silently produces an
empty migration because no tables are registered on Base.metadata.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# --- Make the service package importable when alembic is run from this dir ---
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

# --- Bootstrap settings env vars BEFORE importing the app's settings/models ---
# src/config/settings.py builds ``settings = Settings()`` at import time, which
# requires the DB_* fields. During migrations we only care about the resolved
# DATABASE_URL, so provide harmless placeholders for the required fields if they
# are not already present. Real values (or DATABASE_URL) still take precedence.
_PLACEHOLDER_ENV = {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_USERNAME": "alembic",
    "DB_PASSWORD": "alembic",
    "DB_NAME": "test_management",
    "ALLOW_ORIGINS": "*",
    "SERVICE_NAME": "test-management-service",
    "PORT": "8001",
    "SERVICE_HOSTNAME": "localhost",
}
for _key, _value in _PLACEHOLDER_ENV.items():
    os.environ.setdefault(_key, _value)

# Import Base and resolve the URL the same way the runtime app does.
from src.db.session import ASYNC_DATABASE_URL, Base  # noqa: E402

# Import every model module so all tables register on Base.metadata.
# (Order does not matter; importing the module is what registers the mappers.)
from src.models import (  # noqa: E402,F401
    answer,
    category,
    quiz_session,
    skill,
    test,
    test_skill,
    test_submission,
)

# --- Alembic config ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the resolved async URL (overrides the blank value in alembic.ini).
config.set_main_option("sqlalchemy.url", ASYNC_DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DBAPI connection)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # batch mode keeps ALTER operations portable across SQLite/Postgres.
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via connection.run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
