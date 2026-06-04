import os

# Must be set before any app module is imported so pydantic-settings validation passes.
# Actual DB connection is never made — test_user_service.py overrides get_db with SQLite.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
