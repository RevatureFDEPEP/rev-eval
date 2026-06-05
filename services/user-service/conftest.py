"""
Test bootstrap for user-service.

src.config.settings.Settings() runs at import and requires DB_* + JWT_SECRET.
Set hermetic defaults here before test collection so importing service modules
never opens a real database connection — the engine is created lazily.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-0123456789abcdef-32b")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Preload session to fix circular import order (session imports User model).
import src.db.session  # noqa: E402,F401
