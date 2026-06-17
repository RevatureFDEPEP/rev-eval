"""Alembic environment for reporting-and-analytics-service.

This service owns NO domain tables — it reads test-management's schema over a
read-only engine (see ADR 0001). So ``Base.metadata`` is intentionally empty
and autogenerate produces nothing; the migration chain exists only to give the
service its own ``alembic_version`` bookkeeping in its private datastore,
isolated from test-management's chain in eval_ai_dev.

Improvement over the boilerplate template: the online path reuses the async
``engine`` already constructed in src/db/session.py rather than rebuilding one
from the ini section — one URL/driver resolution, and no configparser
``%``-escaping of DB passwords.
"""
import asyncio
from logging.config import fileConfig

from alembic import context

from src.db.session import ASYNC_DATABASE_URL, Base, engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Keep autogenerate scoped to tables this service actually owns — defensive
    parity, since the private reporting datastore holds only owned tables."""
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=ASYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
