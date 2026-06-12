"""
tests/test_auth_postgres.py

Auth flow integration tests against a real Postgres instance.

Skipped locally (requires the CI Postgres service container).
Covers the gaps that SQLite masks:
- psycopg2 type mapping for user fields
- Unique-email index enforcement at the database level
- Password hash and JWT round-trip against real Postgres rows

Uses setup_class/teardown_class (not module-level dependency_overrides) so
that the override does not persist and corrupt test_user_service.py which
runs after this file and needs its own SQLite override.
"""

import os
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")

_IN_CI = os.environ.get("CI") == "true"

pytestmark = [
    pytest.mark.skipif(
        not _IN_CI,
        reason="Postgres integration tests require CI service container (CI=true)",
    ),
    pytest.mark.asyncio,
]

from main import app  # noqa: E402
from src.db.session import get_db  # noqa: E402
from src.db.init_db import Base  # noqa: E402
from src.models.user import User  # noqa: E402, F401

_PG_URL = "postgresql://test:test@localhost:5432/test"


def _make_pg_session_factory():
    engine = create_engine(_PG_URL)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


class TestAuthFlowPostgres:
    """Register, login, and profile access against real Postgres."""

    pg_engine = None

    @classmethod
    def setup_class(cls):
        cls.pg_engine, factory = _make_pg_session_factory()
        cls._factory = factory

        # Save previous override so teardown can restore it.
        cls._prev_get_db = app.dependency_overrides.get(get_db)

        def pg_get_db():
            db = factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = pg_get_db

    @classmethod
    def teardown_class(cls):
        # Restore whatever test_user_service.py set at module-import time.
        if cls._prev_get_db is not None:
            app.dependency_overrides[get_db] = cls._prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)

        if cls.pg_engine is not None:
            Base.metadata.drop_all(bind=cls.pg_engine)
            cls.pg_engine.dispose()

    @pytest_asyncio.fixture
    async def pg_client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    async def test_register_creates_user_in_postgres(self, pg_client):
        resp = await pg_client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_user@example.com",
                "password": "SecurePass123!",
                "full_name": "PG User",
                "role": "PARTICIPANT",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["user"]["email"] == "pg_user@example.com"
        assert "access_token" in data

    async def test_register_duplicate_email_rejected(self, pg_client):
        payload = {
            "email": "pg_dup@example.com",
            "password": "Pass123!",
            "full_name": "Dup",
            "role": "PARTICIPANT",
        }
        await pg_client.post("/v1/api/auth/register", json=payload)
        resp = await pg_client.post("/v1/api/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    async def test_login_valid_credentials_returns_token(self, pg_client):
        await pg_client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_login@example.com",
                "password": "LoginPass123!",
                "full_name": "Login PG",
                "role": "PARTICIPANT",
            },
        )
        resp = await pg_client.post(
            "/v1/api/auth/login",
            json={"email": "pg_login@example.com", "password": "LoginPass123!"},
        )
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

    async def test_login_wrong_password_rejected(self, pg_client):
        await pg_client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_wrongpass@example.com",
                "password": "CorrectPass123!",
                "full_name": "Wrong Pass",
                "role": "PARTICIPANT",
            },
        )
        resp = await pg_client.post(
            "/v1/api/auth/login",
            json={"email": "pg_wrongpass@example.com", "password": "BadPass123!"},
        )
        assert resp.status_code == 401

    async def test_get_me_with_valid_token(self, pg_client):
        await pg_client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_me@example.com",
                "password": "MePass123!",
                "full_name": "Me User",
                "role": "PARTICIPANT",
            },
        )
        login = await pg_client.post(
            "/v1/api/auth/login",
            json={"email": "pg_me@example.com", "password": "MePass123!"},
        )
        token = login.json()["access_token"]

        resp = await pg_client.get(
            "/v1/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["email"] == "pg_me@example.com"

    async def test_get_user_by_email_postgres(self, pg_client):
        await pg_client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_byemail@example.com",
                "password": "Pass123!",
                "full_name": "By Email PG",
                "role": "PARTICIPANT",
            },
        )
        resp = await pg_client.get(
            "/v1/api/users/by-email/pg_byemail@example.com"
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "pg_byemail@example.com"

    async def test_invite_then_login_fails_postgres(self, pg_client):
        """Invited (inactive) users cannot log in — Postgres enforces same rules."""
        await pg_client.post(
            "/v1/api/users/invite",
            json={"email": "pg_invited@example.com"},
        )
        resp = await pg_client.post(
            "/v1/api/auth/login",
            json={"email": "pg_invited@example.com", "password": "anypass"},
        )
        assert resp.status_code == 401
