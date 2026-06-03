"""Test bootstrap for test-management-service.

`src.config.settings.Settings()` runs at import and requires DB_* plus
ALLOW_ORIGINS / SERVICE_NAME / PORT / SERVICE_HOSTNAME. Set hermetic defaults
here (imported before test collection) so importing the service modules never
opens a real database connection — the async engine is created lazily.
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
