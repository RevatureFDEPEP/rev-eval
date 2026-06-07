"""
Unit tests for AuthService — pure logic + DB-level tests via the db fixture.
"""

import os

# Env vars must be set before any src import; conftest does this but guard here too
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("JWT_SECRET", "test-super-secret-key-for-testing-only")

import pytest  # noqa: E402
from jwt import PyJWTError  # noqa: E402

from src.models.user import UserRole  # noqa: E402
from src.services.auth_service import AuthService  # noqa: E402


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def test_hash_password_is_not_plaintext():
    hashed = AuthService.hash_password("secret")
    assert hashed != "secret"
    assert len(hashed) > 0


def test_verify_password_correct():
    hashed = AuthService.hash_password("secret")
    assert AuthService.verify_password("secret", hashed) is True


def test_verify_password_wrong():
    hashed = AuthService.hash_password("secret")
    assert AuthService.verify_password("wrong", hashed) is False


def test_verify_password_empty_hash():
    assert AuthService.verify_password("secret", "") is False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def test_create_access_token_returns_string():
    token = AuthService.create_access_token({"sub": "1", "email": "a@b.com"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_roundtrip():
    payload = {"sub": "42", "email": "a@b.com"}
    token = AuthService.create_access_token(payload)
    decoded = AuthService.decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["email"] == "a@b.com"


def test_decode_access_token_invalid_raises():
    with pytest.raises(PyJWTError):
        AuthService.decode_access_token("this.is.garbage")


# ---------------------------------------------------------------------------
# DB-dependent tests
# ---------------------------------------------------------------------------

def test_create_user_stores_hash_not_plaintext(db):
    user = AuthService.create_user(
        db,
        email="hash_test@example.com",
        password="plainpass",
        full_name="Hash Test",
        role=UserRole.PARTICIPANT,
    )
    assert user.password_hash != "plainpass"
    assert user.password_hash is not None


def test_create_user_splits_full_name(db):
    user = AuthService.create_user(
        db,
        email="name_split@example.com",
        password="password123",
        full_name="John Doe",
        role=UserRole.PARTICIPANT,
    )
    assert user.first_name == "John"
    assert user.last_name == "Doe"


def test_get_user_by_email_found(db):
    AuthService.create_user(
        db,
        email="found@example.com",
        password="password123",
        role=UserRole.PARTICIPANT,
    )
    user = AuthService.get_user_by_email(db, "found@example.com")
    assert user is not None
    assert user.email == "found@example.com"


def test_get_user_by_email_not_found(db):
    user = AuthService.get_user_by_email(db, "nobody@example.com")
    assert user is None


def test_authenticate_user_success(db):
    AuthService.create_user(
        db,
        email="auth_ok@example.com",
        password="correctpass123",
        role=UserRole.PARTICIPANT,
    )
    result = AuthService.authenticate_user(db, "auth_ok@example.com", "correctpass123")
    assert result is not None
    assert result.email == "auth_ok@example.com"


def test_authenticate_user_wrong_password(db):
    AuthService.create_user(
        db,
        email="auth_wrong@example.com",
        password="correctpass123",
        role=UserRole.PARTICIPANT,
    )
    result = AuthService.authenticate_user(db, "auth_wrong@example.com", "wrongpass")
    assert result is None


def test_authenticate_user_inactive(db):
    user = AuthService.create_user(
        db,
        email="inactive@example.com",
        password="password123",
        role=UserRole.PARTICIPANT,
    )
    user.is_active = False
    db.commit()

    result = AuthService.authenticate_user(db, "inactive@example.com", "password123")
    assert result is None


def test_authenticate_user_not_found(db):
    result = AuthService.authenticate_user(db, "ghost@example.com", "password123")
    assert result is None
