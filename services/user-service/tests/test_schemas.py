import pytest
from pydantic import ValidationError
from src.schemas.auth_schema import LoginRequest, RegisterRequest
from src.schemas.user_schema import UserCreate, UserUpdate
from src.models.user import UserRole


class TestLoginRequest:
    @pytest.mark.parametrize("email,password", [
        ("user@example.com", "secret"),
        ("trainer@org.net", "p@ssw0rd"),
        ("a+b@sub.domain.io", "x" * 50),
    ])
    def test_valid_credentials(self, email, password):
        req = LoginRequest(email=email, password=password)
        assert req.email == email
        assert req.password == password

    @pytest.mark.parametrize("bad_email", [
        "notanemail",
        "missing@",
        "@nodomain",
        "no-at-sign",
    ])
    def test_invalid_email_rejected(self, bad_email):
        with pytest.raises(ValidationError):
            LoginRequest(email=bad_email, password="secret")

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

    def test_missing_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")


class TestRegisterRequest:
    def test_default_role_is_participant(self):
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.role == UserRole.PARTICIPANT

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_explicit_role_accepted(self, role):
        req = RegisterRequest(email="user@example.com", password="password123", role=role)
        assert req.role == role

    @pytest.mark.parametrize("short_pw", ["short", "1234567", "a" * 7])
    def test_password_below_minimum_rejected(self, short_pw):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password=short_pw)

    @pytest.mark.parametrize("valid_pw", ["password123", "a" * 8, "a" * 128])
    def test_valid_password_lengths_accepted(self, valid_pw):
        req = RegisterRequest(email="user@example.com", password=valid_pw)
        assert len(req.password) >= 8

    def test_optional_full_name(self):
        req = RegisterRequest(email="user@example.com", password="password123", full_name="Jane Doe")
        assert req.full_name == "Jane Doe"

    def test_full_name_defaults_none(self):
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.full_name is None


class TestUserCreate:
    @pytest.mark.parametrize("password", [
        "a" * 8,    # minimum
        "a" * 64,   # mid-range
        "a" * 128,  # maximum
    ])
    def test_valid_password_at_boundaries(self, password):
        user = UserCreate(email="user@example.com", role=UserRole.PARTICIPANT, password=password)
        assert user.password == password

    @pytest.mark.parametrize("password", [
        "a" * 7,    # one below min
        "a" * 129,  # one above max
    ])
    def test_invalid_password_at_boundaries(self, password):
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com", role=UserRole.PARTICIPANT, password=password)

    @pytest.mark.parametrize("first,last", [
        ("Jane", "Doe"),
        (None, None),
        ("Single", None),
    ])
    def test_optional_name_fields(self, first, last):
        user = UserCreate(
            email="u@example.com",
            role=UserRole.TRAINER,
            password="password123",
            first_name=first,
            last_name=last,
        )
        assert user.first_name == first
        assert user.last_name == last

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_both_roles_accepted(self, role):
        user = UserCreate(email="r@example.com", role=role, password="password123")
        assert user.role == role


class TestUserUpdate:
    def test_all_fields_optional(self):
        update = UserUpdate()
        assert update.email is None
        assert update.first_name is None
        assert update.last_name is None
        assert update.role is None
        assert update.is_active is None

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_role_update_accepted(self, role):
        update = UserUpdate(role=role)
        assert update.role == role

    @pytest.mark.parametrize("active", [True, False])
    def test_is_active_update(self, active):
        update = UserUpdate(is_active=active)
        assert update.is_active == active

    def test_partial_update_only_email(self):
        update = UserUpdate(email="new@example.com")
        assert update.email == "new@example.com"
        assert update.role is None
