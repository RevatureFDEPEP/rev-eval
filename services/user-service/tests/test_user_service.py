import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from src.db.session import get_db
from src.db.init_db import Base
from src.models.user import User  # registers User table with Base so create_all knows about it

# Use SQLite instead of real PostgreSQL — no DB server needed for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in SQLite before any test runs
Base.metadata.create_all(bind=engine)

def override_get_db():
    # Replaces FastAPI's real PostgreSQL session with a SQLite test session
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Tell FastAPI to use our test DB for every request
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestAuth:
    def test_register_valid_user(self):
        response = client.post("/v1/api/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "role": "PARTICIPANT"
        })
        assert response.status_code == 201
        # Register returns AuthResponse: {access_token, token_type, user: {...}}
        # so email lives one level deeper inside "user"
        assert response.json()["user"]["email"] == "test@example.com"

    def test_register_duplicate_email(self):
        # First registration succeeds
        client.post("/v1/api/auth/register", json={
            "email": "dup@example.com",
            "password": "Pass123!",
            "full_name": "User 1",
            "role": "TRAINER"
        })
        # Same email again must be rejected with 400
        response = client.post("/v1/api/auth/register", json={
            "email": "dup@example.com",
            "password": "Pass123!",
            "full_name": "User 2",
            "role": "PARTICIPANT"
        })
        assert response.status_code == 400
        # auth_route.py raises: detail="Email already registered"
        assert "already registered" in response.json()["detail"].lower()

    def test_login_valid_credentials(self):
        # Register the user first so they exist in the DB
        client.post("/v1/api/auth/register", json={
            "email": "login@example.com",
            "password": "Password123!",
            "full_name": "Login User",
            "role": "PARTICIPANT"
        })
        response = client.post("/v1/api/auth/login", json={
            "email": "login@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_login_invalid_password(self):
        client.post("/v1/api/auth/register", json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "full_name": "User",
            "role": "PARTICIPANT"
        })
        response = client.post("/v1/api/auth/login", json={
            "email": "wrongpass@example.com",
            "password": "WrongPass123!"
        })
        assert response.status_code == 401
        # auth_route.py raises: detail="Incorrect email or password"
        assert "incorrect" in response.json()["detail"].lower()


class TestUser:
    def test_get_user_by_id(self):
        reg_resp = client.post("/v1/api/auth/register", json={
            "email": "getuser@example.com",
            "password": "Pass123!",
            "full_name": "Get User Test",
            "role": "PARTICIPANT"
        })
        # id is nested inside "user" in AuthResponse, not at the top level
        user_id = reg_resp.json()["user"]["id"]

        response = client.get(f"/v1/api/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["email"] == "getuser@example.com"

    def test_update_user(self):
        reg_resp = client.post("/v1/api/auth/register", json={
            "email": "update@example.com",
            "password": "Pass123!",
            "full_name": "Update Me",
            "role": "PARTICIPANT"
        })
        user_id = reg_resp.json()["user"]["id"]

        # Route is PATCH not PUT; UserUpdate schema has first_name/last_name, not full_name
        response = client.patch(f"/v1/api/users/{user_id}", json={
            "first_name": "Updated"
        })
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"
