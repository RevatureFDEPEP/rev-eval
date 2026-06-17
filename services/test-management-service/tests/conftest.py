# Set env vars BEFORE any app/settings import so pydantic-settings does not fail
# when future tests import the FastAPI app or db layer.
import os

# DATABASE_URL must name a driver that is installed in CI. CI installs ONLY
# requirements.txt (which ships asyncpg + psycopg2-binary) plus pytest/pytest-cov/
# ruff — it does NOT install aiosqlite. A `sqlite+aiosqlite://` URL would make
# `src.db.session` raise ModuleNotFoundError at import time, because
# `create_async_engine` imports the dialect's DBAPI eagerly when the engine is
# constructed (module top-level), long before any connection is opened. asyncpg
# is in requirements.txt and constructs an engine fine without a live DB, and no
# test ever opens a connection (every test overrides `get_db` with a mocked
# AsyncSession), so this URL is import-safe and never dials Postgres.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_management"
)
os.environ.setdefault("JWT_SECRET", "test-super-secret-key-for-testing-only")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test_management")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
