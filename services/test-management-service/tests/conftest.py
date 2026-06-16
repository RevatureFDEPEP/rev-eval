# Set env vars BEFORE any app/settings import so pydantic-settings does not fail
# when future tests import the FastAPI app or db layer.
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-super-secret-key-for-testing-only")
