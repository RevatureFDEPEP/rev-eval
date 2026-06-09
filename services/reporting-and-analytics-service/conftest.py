"""Test bootstrap for reporting-and-analytics-service.

`src.config.settings.Settings()` runs at import and requires DB_*. Set hermetic
defaults here (imported before test collection) so importing the service
modules never touches a real database — the async engine is created lazily and
these tests never open a connection.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
