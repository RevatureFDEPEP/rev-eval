"""Smoke / sanity tests for user-service.

No DB required. These cover bcrypt password hashing, HS256 JWT issue/verify
round-trips, the UserRole enum, and Pydantic request-schema validation.
"""
from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError
from src.models.user import UserRole
from src.schemas.auth_schema import RegisterRequest
from src.services.auth_service import AuthService


def test_password_hash_roundtrip():
    hashed = AuthService.hash_password("password123")
    assert hashed != "password123"
    assert AuthService.verify_password("password123", hashed) is True
    assert AuthService.verify_password("wrong-password", hashed) is False


def test_verify_password_empty_hash_is_false():
    assert AuthService.verify_password("anything", "") is False


def test_access_token_roundtrip():
    token = AuthService.create_access_token(
        {"sub": "42", "email": "a@b.com", "role": "PARTICIPANT"}
    )
    payload = AuthService.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.com"
    assert "exp" in payload


def test_expired_token_is_rejected():
    token = AuthService.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.PyJWTError):
        AuthService.decode_access_token(token)


def test_user_role_values():
    assert UserRole.TRAINER == "TRAINER"
    assert UserRole.PARTICIPANT == "PARTICIPANT"
    assert {r.value for r in UserRole} == {"TRAINER", "PARTICIPANT"}


@pytest.mark.parametrize("email", ["a@b.com", "first.last@example.io"])
def test_register_request_valid(email):
    req = RegisterRequest(email=email, password="longenough")
    assert req.role == UserRole.PARTICIPANT


def test_register_request_short_password_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="short")


def test_register_request_bad_email_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="longenough")
