# IMPORTANT: set env vars BEFORE any app imports so pydantic-settings picks them up
import os

os.environ.update(
    {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USERNAME": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_NAME": "testdb",
        "JWT_SECRET": "test-super-secret-key-for-testing-only",
    }
)

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

# Import Base from init_db (the canonical definition); session re-exports it.
from src.db.init_db import Base  # noqa: E402
from src.db.session import get_db  # noqa: E402

# Register the User model so its table is included in Base.metadata
from src.models.user import User  # noqa: E402, F401

# ---------------------------------------------------------------------------
# SQLite in-memory engine
#
# StaticPool forces all connections — including those created in worker
# threads by anyio/starlette — to reuse the same underlying SQLite
# connection, which means the in-memory database remains visible across
# threads.
# ---------------------------------------------------------------------------
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db():
    """Create all tables, yield a session, then drop everything."""
    Base.metadata.create_all(engine_test, checkfirst=True)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine_test)


def _override_get_db(session):
    """Return a generator that yields the provided session (matches get_db signature)."""

    def _get_db():
        try:
            yield session
        finally:
            pass  # session lifecycle managed by the db fixture

    return _get_db


@pytest.fixture(scope="function")
def client(db):
    """TestClient wired to the in-memory SQLite DB with init_db patched out."""
    with patch("main.init_db", return_value=None):
        from main import app

        # Override get_db with a generator that yields the test session
        app.dependency_overrides[get_db] = _override_get_db(db)

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Register a test user and return the Authorization header dict."""
    resp = client.post(
        "/v1/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "role": "PARTICIPANT",
        },
    )
    assert resp.status_code == 201, f"auth_headers fixture failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
