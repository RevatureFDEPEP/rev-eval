"""
Test bootstrap for test-management-service.

src.config.settings.Settings() runs at import and requires DB_* plus several
service-specific vars. Set hermetic defaults here before test collection.
DATABASE_URL overrides the async engine so repository tests can use SQLite.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "eval_ai_dev")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("QUESTION_SERVICE_URL", "http://localhost:8003")
