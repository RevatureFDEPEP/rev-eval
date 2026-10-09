"""
tests/test_auth_postgres.py

Auth flow integration tests against a real Postgres instance.

Skipped locally (requires the CI Postgres service container).
Covers the gaps that SQLite masks:
- psycopg2 type mapping for user fields
- Unique-email index enforcement at the database level
- Password hash and JWT round-trip against real Postgres rows

Uses sync TestClient (matching user-service's sync SQLAlchemy) with
setup_class/teardown_class so the override does not persist and corrupt
test_user_service.py which runs after this file.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")

_IN_CI = os.environ.get("CI") == "true"

pytestmark = pytest.mark.skipif(
    not _IN_CI,
    reason="Postgres integration tests require CI service container (CI=true)",
)

from main import app  # noqa: E402
from src.db.session import get_db  # noqa: E402
from src.db.init_db import Base  # noqa: E402
from src.models.user import User  # noqa: E402, F401

_PG_URL = "postgresql://test:test@localhost:5432/test"


class TestAuthFlowPostgres:
    """Register, login, and profile access against real Postgres."""

    pg_engine = None

    @classmethod
    def setup_class(cls):
        cls.pg_engine = create_engine(_PG_URL)
        Base.metadata.drop_all(bind=cls.pg_engine)
        Base.metadata.create_all(bind=cls.pg_engine)
        factory = sessionmaker(autocommit=False, autoflush=False, bind=cls.pg_engine)

        cls._prev_get_db = app.dependency_overrides.get(get_db)

        def pg_get_db():
            db = factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = pg_get_db
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        if cls._prev_get_db is not None:
            app.dependency_overrides[get_db] = cls._prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)

        if cls.pg_engine is not None:
            Base.metadata.drop_all(bind=cls.pg_engine)
            cls.pg_engine.dispose()

    def test_register_creates_user_in_postgres(self):
        resp = self.client.post(
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

    def test_register_duplicate_email_rejected(self):
        payload = {
            "email": "pg_dup@example.com",
            "password": "Pass123!",
            "full_name": "Dup",
            "role": "PARTICIPANT",
        }
        self.client.post("/v1/api/auth/register", json=payload)
        resp = self.client.post("/v1/api/auth/register", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_login_valid_credentials_returns_token(self):
        self.client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_login@example.com",
                "password": "LoginPass123!",
                "full_name": "Login PG",
                "role": "PARTICIPANT",
            },
        )
        resp = self.client.post(
            "/v1/api/auth/login",
            json={"email": "pg_login@example.com", "password": "LoginPass123!"},
        )
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

    def test_login_wrong_password_rejected(self):
        self.client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_wrongpass@example.com",
                "password": "CorrectPass123!",
                "full_name": "Wrong Pass",
                "role": "PARTICIPANT",
            },
        )
        resp = self.client.post(
            "/v1/api/auth/login",
            json={"email": "pg_wrongpass@example.com", "password": "BadPass123!"},
        )
        assert resp.status_code == 401

    def test_get_me_with_valid_token(self):
        self.client.post(
            "/v1/api/auth/register",
            json={
                "email": "pg_me@example.com",
                "password": "MePass123!",
                "full_name": "Me User",
                "role": "PARTICIPANT",
            },
        )
        login = self.client.post(
            "/v1/api/auth/login",
            json={"email": "pg_me@example.com", "password": "MePass123!"},
        )
        token = login.json()["access_token"]

        resp = self.client.get(
            "/v1/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["email"] == "pg_me@example.com"

    def _token(self, email: str, role: str) -> dict:
        reg = self.client.post(
            "/v1/api/auth/register",
            json={"email": email, "password": "Pass123!", "full_name": "PG User", "role": role},
        )
        assert reg.status_code in (200, 201), reg.text
        return {"Authorization": f"Bearer {reg.json()['access_token']}"}

    def test_get_user_by_email_postgres(self):
        me = self._token("pg_byemail@example.com", "PARTICIPANT")
        resp = self.client.get("/v1/api/users/by-email/pg_byemail@example.com", headers=me)
        assert resp.status_code == 200
        assert resp.json()["email"] == "pg_byemail@example.com"

    def test_invite_then_login_fails_postgres(self):
        """Invited (inactive) users cannot log in — Postgres enforces same rules."""
        trainer = self._token("pg_trainer@example.com", "TRAINER")
        invite = self.client.post(
            "/v1/api/users/invite",
            json={"email": "pg_invited@example.com"},
            headers=trainer,
        )
        assert invite.status_code == 201, invite.text
        resp = self.client.post(
            "/v1/api/auth/login",
            json={"email": "pg_invited@example.com", "password": "anypass"},
        )
        assert resp.status_code == 401

    def test_participant_cannot_escalate_role_postgres(self):
        """A denied self role change leaves the Postgres row unchanged."""
        me = self._token("pg_escalate@example.com", "PARTICIPANT")
        user_id = self.client.get("/v1/api/users/me", headers=me).json()["id"]
        resp = self.client.patch(f"/v1/api/users/{user_id}", json={"role": "TRAINER"}, headers=me)
        assert resp.status_code == 403
        assert self.client.get("/v1/api/users/me", headers=me).json()["role"] == "PARTICIPANT"
