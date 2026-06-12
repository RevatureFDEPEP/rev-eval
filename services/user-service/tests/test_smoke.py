"""
Smoke tests for user-service — no database required.

Covers: bcrypt password hashing, HS256 JWT round-trips, UserRole enum,
and Pydantic request-schema validation.
"""
from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError
from src.models.user import UserRole
from src.schemas.auth_schema import LoginRequest, RegisterRequest
from src.schemas.user_schema import InviteUserRequest, UserCreate
from src.services.auth_service import AuthService

# ── Password hashing ─────────────────────────────────────────────────────────

def test_password_hash_roundtrip():
    hashed = AuthService.hash_password("password123")
    assert hashed != "password123"
    assert AuthService.verify_password("password123", hashed) is True
    assert AuthService.verify_password("wrong-password", hashed) is False


def test_verify_password_empty_hash_returns_false():
    assert AuthService.verify_password("anything", "") is False


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_access_token_roundtrip():
    token = AuthService.create_access_token(
        {"sub": "42", "email": "a@b.com", "role": "PARTICIPANT"}
    )
    payload = AuthService.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.com"
    assert "exp" in payload


def test_expired_token_is_rejected():
    token = AuthService.create_access_token(
        {"sub": "1"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(jwt.PyJWTError):
        AuthService.decode_access_token(token)


# ── UserRole enum ─────────────────────────────────────────────────────────────

def test_user_role_values():
    assert UserRole.TRAINER == "TRAINER"
    assert UserRole.PARTICIPANT == "PARTICIPANT"
    assert {r.value for r in UserRole} == {"TRAINER", "PARTICIPANT"}


# ── LoginRequest schema ───────────────────────────────────────────────────────

@pytest.mark.parametrize("email", [
    "user@example.com",
    "trainer@revature.net",
    "first.last+tag@sub.domain.io",
])
def test_login_request_accepts_valid_email(email):
    req = LoginRequest(email=email, password="anypassword")
    assert req.email == email


@pytest.mark.parametrize("bad_email", [
    "not-an-email",
    "missing-at.com",
    "@nodomain.com",
    "",
])
def test_login_request_rejects_invalid_email(bad_email):
    with pytest.raises(ValidationError):
        LoginRequest(email=bad_email, password="anypassword")


# ── RegisterRequest schema ────────────────────────────────────────────────────

def test_register_request_defaults_to_participant_role():
    req = RegisterRequest(email="new@example.com", password="longenough")
    assert req.role == UserRole.PARTICIPANT


def test_register_request_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="short")


def test_register_request_rejects_bad_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="longenough")


# ── UserCreate schema ─────────────────────────────────────────────────────────

def test_user_create_accepts_trainer_payload():
    user = UserCreate(
        email="trainer@example.com",
        first_name="Test",
        last_name="Trainer",
        role="TRAINER",
        password="Password123!",
    )
    assert user.role == UserRole.TRAINER
    assert user.first_name == "Test"


# ── InviteUserRequest schema ──────────────────────────────────────────────────

def test_invite_user_request_defaults_to_participant_role():
    req = InviteUserRequest(email="invitee@example.com", first_name="Invited", last_name="User")
    assert req.role == UserRole.PARTICIPANT
