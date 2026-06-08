import pytest
from pydantic import ValidationError

from src.models.user import UserRole
from src.schemas.auth_schema import LoginRequest, RegisterRequest


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(email="user@example.com", password="secret")
        assert req.email == "user@example.com"
        assert req.password == "secret"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="secret")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")


class TestRegisterRequest:
    def test_valid_defaults_to_participant(self):
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.role == UserRole.PARTICIPANT
        assert req.full_name is None

    @pytest.mark.parametrize("password", ["short1", "x" * 129])
    def test_password_length_rejected(self, password):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password=password)

    def test_min_password_boundary_accepted(self):
        req = RegisterRequest(email="user@example.com", password="a" * 8)
        assert len(req.password) == 8

    def test_max_password_boundary_accepted(self):
        req = RegisterRequest(email="user@example.com", password="a" * 128)
        assert len(req.password) == 128

    def test_explicit_trainer_role(self):
        req = RegisterRequest(
            email="trainer@example.com",
            password="password123",
            role=UserRole.TRAINER,
        )
        assert req.role == UserRole.TRAINER

    def test_full_name_stored(self):
        req = RegisterRequest(email="user@example.com", password="password123", full_name="Alice")
        assert req.full_name == "Alice"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="bad-email", password="password123")
