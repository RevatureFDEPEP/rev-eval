import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "reporting")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")

from src.config.settings import settings  # noqa: E402

Base = declarative_base()

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
