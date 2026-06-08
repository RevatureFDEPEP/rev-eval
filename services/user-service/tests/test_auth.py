from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError

from src.models.user import UserRole
from src.schemas.auth_schema import RegisterRequest
from src.services.auth_service import AuthService


def test_hash_and_verify_password():
    hashed = AuthService.hash_password("secret123")
    assert AuthService.verify_password("secret123", hashed) is True


def test_verify_wrong_password():
    hashed = AuthService.hash_password("secret123")
    assert AuthService.verify_password("wrong", hashed) is False


def test_verify_empty_hash():
    assert AuthService.verify_password("anything", "") is False


def test_create_and_decode_token():
    token = AuthService.create_access_token(
        {"sub": "42", "role": "TRAINER", "email": "alice@example.com"}
    )
    payload = AuthService.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "TRAINER"
    assert payload["email"] == "alice@example.com"


def test_token_expiry_raises():
    token = AuthService.create_access_token(
        {"sub": "1"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        AuthService.decode_access_token(token)


def test_userrole_trainer_value():
    assert UserRole.TRAINER == "TRAINER"


def test_userrole_participant_value():
    assert UserRole.PARTICIPANT == "PARTICIPANT"


def test_register_request_valid():
    req = RegisterRequest(email="user@example.com", password="password123")
    assert req.email == "user@example.com"


def test_register_request_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="short")


def test_register_request_bad_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="notanemail", password="password123")


def test_register_default_role():
    req = RegisterRequest(email="user@example.com", password="password123")
    assert req.role == UserRole.PARTICIPANT
