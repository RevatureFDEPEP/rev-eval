import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Satisfy pydantic-settings before any src.* import
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "reveval")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

import src.models.quiz_session  # noqa: F401, E402
import src.models.skill  # noqa: F401, E402

# Register all models with Base.metadata so autogenerate sees them
import src.models.test  # noqa: F401, E402
import src.models.test_skill  # noqa: F401, E402
import src.models.test_submission  # noqa: F401, E402
from src.config.settings import settings  # noqa: E402
from src.db.session import Base  # noqa: E402

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata

_db_url = settings.SQLALCHEMY_DATABASE_URL
if _db_url.startswith("postgresql://"):
    ASYNC_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://")
elif _db_url.startswith("postgresql+psycopg2://"):
    ASYNC_URL = _db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
else:
    ASYNC_URL = _db_url


def run_migrations_offline() -> None:
    context.configure(
        url=ASYNC_URL,
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
    engine = create_async_engine(ASYNC_URL)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
