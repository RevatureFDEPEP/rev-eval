import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.db.session import get_db
from src.db.init_db import Base
from src.models.user import User  # noqa: F401 — registers User table with Base so create_all knows about it

# Route handlers use sync Session (db.query/db.add/db.commit), so we must keep a sync
# engine here. sqlite+aiosqlite requires AsyncSession which is incompatible with those
# calls. StaticPool forces all connections to share one in-memory DB — without it each
# new connection gets a fresh empty database and create_all's tables become invisible.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Mark every async test in this module without decorating each one individually
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestAuth:
    async def test_register_valid_user(self, client):
        response = await client.post("/v1/api/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "role": "PARTICIPANT"
        })
        assert response.status_code == 201
        # Register returns AuthResponse: {access_token, token_type, user: {...}}
        # so email lives one level deeper inside "user"
        assert response.json()["user"]["email"] == "test@example.com"

    async def test_register_duplicate_email(self, client):
        # First registration succeeds
        await client.post("/v1/api/auth/register", json={
            "email": "dup@example.com",
            "password": "Pass123!",
            "full_name": "User 1",
            "role": "TRAINER"
        })
        # Same email again must be rejected with 400
        response = await client.post("/v1/api/auth/register", json={
            "email": "dup@example.com",
            "password": "Pass123!",
            "full_name": "User 2",
            "role": "PARTICIPANT"
        })
        assert response.status_code == 400
        # auth_route.py raises: detail="Email already registered"
        assert "already registered" in response.json()["detail"].lower()

    async def test_login_valid_credentials(self, client):
        # Register the user first so they exist in the DB
        await client.post("/v1/api/auth/register", json={
            "email": "login@example.com",
            "password": "Password123!",
            "full_name": "Login User",
            "role": "PARTICIPANT"
        })
        response = await client.post("/v1/api/auth/login", json={
            "email": "login@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    async def test_login_invalid_password(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "full_name": "User",
            "role": "PARTICIPANT"
        })
        response = await client.post("/v1/api/auth/login", json={
            "email": "wrongpass@example.com",
            "password": "WrongPass123!"
        })
        assert response.status_code == 401
        # auth_route.py raises: detail="Incorrect email or password"
        assert "incorrect" in response.json()["detail"].lower()


async def _register(client, email, role="PARTICIPANT"):
    """Register a user and return (id, auth headers carrying their own token)."""
    resp = await client.post("/v1/api/auth/register", json={
        "email": email,
        "password": "Pass123!",
        "full_name": "Test User",
        "role": role,
    })
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['access_token']}"}


def _snapshot(user_id):
    """The stored fields a denied write must leave untouched."""
    db = TestingSessionLocal()
    try:
        u = db.get(User, user_id)
        return (u.email, u.first_name, u.last_name, u.role, u.is_active)
    finally:
        db.close()


def _count_users():
    db = TestingSessionLocal()
    try:
        return db.query(User).count()
    finally:
        db.close()


class TestUser:
    async def test_get_user_by_id(self, client):
        user_id, headers = await _register(client, "getuser@example.com")
        response = await client.get(f"/v1/api/users/{user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "getuser@example.com"

    async def test_update_user(self, client):
        user_id, headers = await _register(client, "update@example.com")
        # Route is PATCH not PUT; UserUpdate schema has first_name/last_name, not full_name
        response = await client.patch(f"/v1/api/users/{user_id}", json={
            "first_name": "Updated"
        }, headers=headers)
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"

    async def test_update_user_name_fields(self, client):
        user_id, headers = await _register(client, "updateall@example.com")
        response = await client.patch(f"/v1/api/users/{user_id}", json={
            "first_name": "New",
            "last_name": "Name",
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "New"
        assert data["last_name"] == "Name"
        assert data["role"] == "PARTICIPANT"

    async def test_get_user_by_id_not_found(self, client):
        _, trainer = await _register(client, "trainer-404@example.com", "TRAINER")
        response = await client.get("/v1/api/users/99999", headers=trainer)
        assert response.status_code == 404

    async def test_get_user_by_email(self, client):
        _, headers = await _register(client, "byemail@example.com")
        response = await client.get("/v1/api/users/by-email/byemail@example.com", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "byemail@example.com"

    async def test_get_user_by_email_not_found(self, client):
        _, trainer = await _register(client, "trainer-email-404@example.com", "TRAINER")
        response = await client.get("/v1/api/users/by-email/nobody@test.com", headers=trainer)
        assert response.status_code == 404

    async def test_list_users(self, client):
        await _register(client, "list1@example.com")
        _, trainer = await _register(client, "trainer-list@example.com", "TRAINER")
        response = await client.get("/v1/api/users/", headers=trainer)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_users_with_role_filter(self, client):
        _, trainer = await _register(client, "trainer1@example.com", "TRAINER")
        response = await client.get("/v1/api/users/?role=TRAINER", headers=trainer)
        assert response.status_code == 200
        users = response.json()
        assert users and all(u["role"] == "TRAINER" for u in users)

    async def test_invite_user_new(self, client):
        _, trainer = await _register(client, "trainer-invite@example.com", "TRAINER")
        response = await client.post("/v1/api/users/invite", json={
            "email": "invited@example.com",
            "first_name": "New",
            "last_name": "Invite",
            "role": "PARTICIPANT"
        }, headers=trainer)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "invited@example.com"

    async def test_invite_user_existing(self, client):
        await _register(client, "existing@example.com")
        _, trainer = await _register(client, "trainer-existing@example.com", "TRAINER")
        response = await client.post("/v1/api/users/invite", json={
            "email": "existing@example.com"
        }, headers=trainer)
        assert response.status_code == 201
        assert "already exists" in response.json()["message"]

    async def test_get_me_with_valid_token(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "getme@example.com",
            "password": "Pass123!",
            "full_name": "Get Me",
            "role": "PARTICIPANT"
        })
        login_resp = await client.post("/v1/api/auth/login", json={
            "email": "getme@example.com",
            "password": "Pass123!"
        })
        token = login_resp.json()["access_token"]

        response = await client.get("/v1/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["email"] == "getme@example.com"

    async def test_get_me_invalid_token(self, client):
        response = await client.get("/v1/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client):
        response = await client.post("/v1/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "Pass123!"
        })
        assert response.status_code == 401

    async def test_login_inactive_invited_user(self, client):
        # Invite creates an inactive user with no password — login must fail
        _, trainer = await _register(client, "trainer-inactive@example.com", "TRAINER")
        await client.post("/v1/api/users/invite", json={
            "email": "inactive@example.com"
        }, headers=trainer)
        response = await client.post("/v1/api/auth/login", json={
            "email": "inactive@example.com",
            "password": "anypass"
        })
        assert response.status_code == 401


class TestUserAuthorization:
    """Who may do what on /users/*, decided from the signed Bearer JWT."""

    @pytest.mark.parametrize("method,path,body", [
        ("GET", "/v1/api/users/me", None),
        ("GET", "/v1/api/users/", None),
        ("GET", "/v1/api/users/1", None),
        ("GET", "/v1/api/users/by-email/someone@example.com", None),
        ("PATCH", "/v1/api/users/1", {"first_name": "X"}),
        ("POST", "/v1/api/users/invite", {"email": "anon-invite@example.com"}),
    ])
    async def test_unauthenticated_is_401(self, client, method, path, body):
        before = _count_users()
        response = await client.request(method, path, json=body)
        assert response.status_code == 401
        assert _count_users() == before

    async def test_invalid_token_is_401(self, client):
        response = await client.get("/v1/api/users/", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401

    async def test_participant_reads_self(self, client):
        user_id, me = await _register(client, "p-self@example.com")
        assert (await client.get("/v1/api/users/me", headers=me)).status_code == 200
        assert (await client.get(f"/v1/api/users/{user_id}", headers=me)).status_code == 200
        by_email = await client.get("/v1/api/users/by-email/p-self@example.com", headers=me)
        assert by_email.status_code == 200
        assert by_email.json()["id"] == user_id

    async def test_participant_reads_other_user_403(self, client):
        other_id, _ = await _register(client, "p-other-target@example.com")
        _, me = await _register(client, "p-other-reader@example.com")
        response = await client.get(f"/v1/api/users/{other_id}", headers=me)
        assert response.status_code == 403

    async def test_participant_cannot_probe_missing_ids(self, client):
        _, me = await _register(client, "p-probe@example.com")
        response = await client.get("/v1/api/users/99998", headers=me)
        assert response.status_code == 403

    async def test_participant_lists_users_403(self, client):
        _, me = await _register(client, "p-list@example.com")
        response = await client.get("/v1/api/users/", headers=me)
        assert response.status_code == 403

    async def test_participant_looks_up_other_email_403(self, client):
        await _register(client, "p-email-target@example.com")
        _, me = await _register(client, "p-email-reader@example.com")
        response = await client.get("/v1/api/users/by-email/p-email-target@example.com", headers=me)
        assert response.status_code == 403

    async def test_participant_invites_403_and_creates_nothing(self, client):
        _, me = await _register(client, "p-invite@example.com")
        before = _count_users()
        response = await client.post("/v1/api/users/invite", json={"email": "p-invitee@example.com"}, headers=me)
        assert response.status_code == 403
        assert _count_users() == before

    async def test_participant_patches_other_user_403_unchanged(self, client):
        other_id, _ = await _register(client, "p-patch-target@example.com")
        _, me = await _register(client, "p-patch-actor@example.com")
        before = _snapshot(other_id)
        response = await client.patch(f"/v1/api/users/{other_id}", json={"first_name": "Hacked"}, headers=me)
        assert response.status_code == 403
        assert _snapshot(other_id) == before

    async def test_participant_role_escalation_403_unchanged(self, client):
        me_id, me = await _register(client, "p-escalate@example.com")
        before = _snapshot(me_id)
        response = await client.patch(f"/v1/api/users/{me_id}", json={"role": "TRAINER"}, headers=me)
        assert response.status_code == 403
        assert _snapshot(me_id) == before

    async def test_participant_is_active_change_403_unchanged(self, client):
        me_id, me = await _register(client, "p-active@example.com")
        before = _snapshot(me_id)
        response = await client.patch(f"/v1/api/users/{me_id}", json={"is_active": False}, headers=me)
        assert response.status_code == 403
        assert _snapshot(me_id) == before

    async def test_mixed_patch_with_privileged_field_changes_nothing(self, client):
        me_id, me = await _register(client, "p-mixed@example.com")
        before = _snapshot(me_id)
        response = await client.patch(
            f"/v1/api/users/{me_id}", json={"first_name": "Sneaky", "role": "TRAINER"}, headers=me
        )
        assert response.status_code == 403
        assert _snapshot(me_id) == before

    async def test_email_change_403_unchanged(self, client):
        me_id, me = await _register(client, "p-email-change@example.com")
        before = _snapshot(me_id)
        response = await client.patch(f"/v1/api/users/{me_id}", json={"email": "new@example.com"}, headers=me)
        assert response.status_code == 403
        assert _snapshot(me_id) == before

    async def test_trainer_administrative_reads_allowed(self, client):
        participant_id, _ = await _register(client, "t-read-target@example.com")
        _, trainer = await _register(client, "t-reader@example.com", "TRAINER")
        assert (await client.get(f"/v1/api/users/{participant_id}", headers=trainer)).status_code == 200
        by_email = await client.get("/v1/api/users/by-email/t-read-target@example.com", headers=trainer)
        assert by_email.status_code == 200
        listed = await client.get("/v1/api/users/?role=PARTICIPANT&limit=1000", headers=trainer)
        assert listed.status_code == 200
        assert any(u["id"] == participant_id for u in listed.json())

    async def test_trainer_invites_participant(self, client):
        _, trainer = await _register(client, "t-inviter@example.com", "TRAINER")
        response = await client.post("/v1/api/users/invite", json={"email": "t-invitee@example.com"}, headers=trainer)
        assert response.status_code == 201
        lookup = await client.get("/v1/api/users/by-email/t-invitee@example.com", headers=trainer)
        assert lookup.json()["role"] == "PARTICIPANT"
        assert lookup.json()["is_active"] is False

    async def test_trainer_cannot_invite_trainer(self, client):
        _, trainer = await _register(client, "t-invite-trainer@example.com", "TRAINER")
        before = _count_users()
        response = await client.post(
            "/v1/api/users/invite", json={"email": "t-new-trainer@example.com", "role": "TRAINER"}, headers=trainer
        )
        assert response.status_code == 403
        assert _count_users() == before

    async def test_trainer_cannot_patch_other_user(self, client):
        participant_id, _ = await _register(client, "t-patch-target@example.com")
        _, trainer = await _register(client, "t-patcher@example.com", "TRAINER")
        before = _snapshot(participant_id)
        response = await client.patch(
            f"/v1/api/users/{participant_id}", json={"is_active": False}, headers=trainer
        )
        assert response.status_code == 403
        assert _snapshot(participant_id) == before
