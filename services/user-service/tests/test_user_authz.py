"""Phase 1 regression tests: user-service authorization boundaries.

Covers anonymous lockout, participant self-service limits, privileged-field
tampering, and admin capabilities. Auth/DB dependencies are overridden so the
route authorization logic is exercised without a live database or real JWTs.
"""
from datetime import datetime

import main
import pytest
from fastapi.testclient import TestClient
from src.db.session import get_db
from src.models.user import User, UserRole
from src.services.user_service import UserService
from src.utils import dependencies as deps


def _user(**overrides):
    data = {
        "id": 1,
        "email": "participant@example.com",
        "password_hash": "hashed",
        "full_name": "Pat Participant",
        "first_name": "Pat",
        "last_name": "Participant",
        "role": UserRole.PARTICIPANT,
        "is_active": True,
        "organization_id": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_login": None,
    }
    data.update(overrides)
    return User(**data)


class _FakeDb:
    """Minimal stand-in: PATCH commits/refreshes the in-memory user."""

    def commit(self):
        pass

    def refresh(self, obj):
        pass


@pytest.fixture
def client():
    c = TestClient(main.app)
    main.app.dependency_overrides[get_db] = lambda: _FakeDb()
    yield c
    main.app.dependency_overrides.clear()


def _as(user):
    """Force the JWT-resolving dependencies to yield `user` (or None)."""
    main.app.dependency_overrides[deps.get_current_user] = lambda: user
    main.app.dependency_overrides[deps.get_current_user_optional] = lambda: user


# --- Anonymous lockout -------------------------------------------------------

def test_anonymous_cannot_list_users(client):
    assert client.get("/v1/api/users/").status_code in (401, 403)


def test_anonymous_cannot_read_user(client):
    assert client.get("/v1/api/users/5").status_code in (401, 403)


def test_anonymous_cannot_lookup_by_email(client):
    assert client.get("/v1/api/users/by-email/x@example.com").status_code in (401, 403)


def test_anonymous_cannot_invite(client):
    resp = client.post("/v1/api/users/invite", json={"email": "x@example.com"})
    assert resp.status_code in (401, 403)


# --- Participant restrictions -------------------------------------------------

def test_participant_cannot_list_users(client):
    _as(_user(id=1, role=UserRole.PARTICIPANT))
    assert client.get("/v1/api/users/").status_code == 403


def test_participant_cannot_read_another_user(client):
    _as(_user(id=1, role=UserRole.PARTICIPANT))
    assert client.get("/v1/api/users/999").status_code == 403


def test_participant_can_read_self(client, monkeypatch):
    me = _user(id=7, role=UserRole.PARTICIPANT)
    _as(me)
    monkeypatch.setattr(UserService, "get_user_by_id", lambda db, uid: me)
    resp = client.get("/v1/api/users/7")
    assert resp.status_code == 200
    assert resp.json()["id"] == 7


def test_participant_cannot_update_another_user(client):
    _as(_user(id=1, role=UserRole.PARTICIPANT))
    resp = client.patch("/v1/api/users/2", json={"first_name": "Hax"})
    assert resp.status_code == 403


def test_participant_cannot_change_own_role(client):
    _as(_user(id=3, role=UserRole.PARTICIPANT))
    resp = client.patch("/v1/api/users/3", json={"role": "ADMIN"})
    assert resp.status_code == 403


def test_participant_cannot_change_own_is_active(client):
    _as(_user(id=3, role=UserRole.PARTICIPANT))
    resp = client.patch("/v1/api/users/3", json={"is_active": False})
    assert resp.status_code == 403


def test_participant_can_update_own_safe_fields(client, monkeypatch):
    me = _user(id=3, role=UserRole.PARTICIPANT)
    _as(me)
    monkeypatch.setattr(UserService, "get_user_by_id", lambda db, uid: me)
    resp = client.patch("/v1/api/users/3", json={"first_name": "Patricia"})
    assert resp.status_code == 200
    assert me.first_name == "Patricia"


# --- Admin capabilities -------------------------------------------------------

def test_admin_can_list_users(client, monkeypatch):
    _as(_user(id=1, role=UserRole.ADMIN))
    monkeypatch.setattr(UserService, "list_users", lambda **kw: [])
    assert client.get("/v1/api/users/").status_code == 200


def test_admin_can_change_role_and_status(client, monkeypatch):
    target = _user(id=9, role=UserRole.PARTICIPANT, is_active=True)
    _as(_user(id=1, role=UserRole.ADMIN))
    monkeypatch.setattr(UserService, "get_user_by_id", lambda db, uid: target)
    resp = client.patch("/v1/api/users/9", json={"role": "TRAINER", "is_active": False})
    assert resp.status_code == 200
    assert target.role == UserRole.TRAINER
    assert target.is_active is False


# --- Internal-key bypass ------------------------------------------------------

def test_internal_key_allows_by_email_lookup(client, monkeypatch):
    monkeypatch.setattr(deps.settings, "INTERNAL_API_KEY", "secret-key")
    found = _user(id=2, email="found@example.com")
    monkeypatch.setattr(UserService, "get_user_by_email", lambda db, email: found)
    resp = client.get(
        "/v1/api/users/by-email/found@example.com",
        headers={"X-Internal-Key": "secret-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "found@example.com"


def test_wrong_internal_key_rejected(client, monkeypatch):
    monkeypatch.setattr(deps.settings, "INTERNAL_API_KEY", "secret-key")
    resp = client.get(
        "/v1/api/users/by-email/found@example.com",
        headers={"X-Internal-Key": "wrong"},
    )
    assert resp.status_code in (401, 403)
