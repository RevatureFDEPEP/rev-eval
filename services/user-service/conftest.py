"""Test bootstrap for user-service.

`src.config.settings.Settings()` runs at import and requires DB_* + JWT_SECRET.
Set hermetic defaults here (imported before test collection) so importing the
service modules never touches a real database — the engine is created lazily
and these tests never open a connection.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-0123456789abcdef-32b")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# src/db/session.py and src/models/user.py import each other (session re-exports
# Base and imports User to register it). It only resolves when session loads
# first — the order main.py uses. Preload it here so tests can import models in
# any order. Engine creation is lazy, so no DB connection is opened.
import src.db.session  # noqa: E402,F401
