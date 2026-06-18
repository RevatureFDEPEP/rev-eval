"""
Test bootstrap for reporting-and-analytics-service.

src.config.settings.Settings() runs at import; set hermetic defaults here
before test collection. DATABASE_URL overrides the async engine so tests use
in-memory SQLite instead of Postgres.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "eval_ai_dev")
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SERVICE_NAME", "reporting-and-analytics-service")
os.environ.setdefault("PORT", "8004")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
