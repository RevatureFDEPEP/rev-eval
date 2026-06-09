import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import Base and every model so they register on Base.metadata —
# autogenerate diffs the metadata against the live DB. No reporting models
# exist yet (this is the W2-M10 scaffold); W4-F1 adds them here, kept in sync
# with src/db/session.py. Example once they land:
#     from src.models.report import Report  # noqa: F401
from src.db.session import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve the DB URL the same way src/db/session.py does (env first,
    then settings) and force the asyncpg driver for the async engine."""
    from src.config.settings import settings

    url = os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url


# alembic.ini leaves sqlalchemy.url blank; set it at runtime. Escape '%'
# so configparser interpolation can't choke on password characters.
config.set_main_option("sqlalchemy.url", _database_url().replace("%", "%%"))


def include_object(object, name, type_, reflected, compare_to):
    """Restrict autogenerate to tables in this service's metadata.

    eval_ai_reporting is private to this service (not shared), so today this
    filter is defensive parity with the other services — it keeps autogenerate
    scoped to owned tables if the datastore ever gains externally-managed ones.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
