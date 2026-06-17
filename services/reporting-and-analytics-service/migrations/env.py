import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.db.session import ASYNC_DATABASE_URL, Base

# This service currently owns NO tables — it reads test-management's data from
# the shared database. So there are no model imports here and target_metadata is
# empty; autogenerate produces nothing until reporting gains tables of its own.
#
# version_table is isolated ("reporting_alembic_version") so this env never
# touches the "alembic_version" row that test-management-service owns in the
# same database (see adr/0001-cross-service-data-access.md).
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

VERSION_TABLE = "reporting_alembic_version"


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=ASYNC_DATABASE_URL,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the async engine."""
    connectable = create_async_engine(ASYNC_DATABASE_URL, future=True)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
