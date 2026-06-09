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


class TestUser:
    async def test_get_user_by_id(self, client):
        reg_resp = await client.post("/v1/api/auth/register", json={
            "email": "getuser@example.com",
            "password": "Pass123!",
            "full_name": "Get User Test",
            "role": "PARTICIPANT"
        })
        # id is nested inside "user" in AuthResponse, not at the top level
        user_id = reg_resp.json()["user"]["id"]

        response = await client.get(f"/v1/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "getuser@example.com"

    async def test_update_user(self, client):
        reg_resp = await client.post("/v1/api/auth/register", json={
            "email": "update@example.com",
            "password": "Pass123!",
            "full_name": "Update Me",
            "role": "PARTICIPANT"
        })
        user_id = reg_resp.json()["user"]["id"]

        # Route is PATCH not PUT; UserUpdate schema has first_name/last_name, not full_name
        response = await client.patch(f"/v1/api/users/{user_id}", json={
            "first_name": "Updated"
        })
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"

    async def test_update_user_all_fields(self, client):
        reg_resp = await client.post("/v1/api/auth/register", json={
            "email": "updateall@example.com",
            "password": "Pass123!",
            "full_name": "Original Name",
            "role": "PARTICIPANT"
        })
        user_id = reg_resp.json()["user"]["id"]

        response = await client.patch(f"/v1/api/users/{user_id}", json={
            "first_name": "New",
            "last_name": "Name",
            "role": "TRAINER",
            "is_active": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["last_name"] == "Name"
        assert data["role"] == "TRAINER"

    async def test_update_user_not_found(self, client):
        response = await client.patch("/v1/api/users/99999", json={"first_name": "X"})
        assert response.status_code == 404

    async def test_get_user_by_id_not_found(self, client):
        response = await client.get("/v1/api/users/99999")
        assert response.status_code == 404

    async def test_get_user_by_email(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "byemail@example.com",
            "password": "Pass123!",
            "full_name": "By Email",
            "role": "PARTICIPANT"
        })
        response = await client.get("/v1/api/users/by-email/byemail@example.com")
        assert response.status_code == 200
        assert response.json()["email"] == "byemail@example.com"

    async def test_get_user_by_email_not_found(self, client):
        response = await client.get("/v1/api/users/by-email/nobody@test.com")
        assert response.status_code == 404

    async def test_list_users(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "list1@example.com",
            "password": "Pass123!",
            "full_name": "List User",
            "role": "PARTICIPANT"
        })
        response = await client.get("/v1/api/users/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_users_with_role_filter(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "trainer1@example.com",
            "password": "Pass123!",
            "full_name": "Trainer One",
            "role": "TRAINER"
        })
        response = await client.get("/v1/api/users/?role=TRAINER")
        assert response.status_code == 200
        users = response.json()
        assert all(u["role"] == "TRAINER" for u in users)

    async def test_invite_user_new(self, client):
        response = await client.post("/v1/api/users/invite", json={
            "email": "invited@example.com",
            "first_name": "New",
            "last_name": "Invite",
            "role": "PARTICIPANT"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "invited@example.com"

    async def test_invite_user_existing(self, client):
        await client.post("/v1/api/auth/register", json={
            "email": "existing@example.com",
            "password": "Pass123!",
            "full_name": "Existing User",
            "role": "PARTICIPANT"
        })
        response = await client.post("/v1/api/users/invite", json={
            "email": "existing@example.com"
        })
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
        await client.post("/v1/api/users/invite", json={
            "email": "inactive@example.com"
        })
        response = await client.post("/v1/api/auth/login", json={
            "email": "inactive@example.com",
            "password": "anypass"
        })
        assert response.status_code == 401
