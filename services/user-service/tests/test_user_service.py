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
