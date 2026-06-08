import pytest
from pydantic import ValidationError

from src.models.user import UserRole
from src.schemas.user_schema import InviteUserRequest, UserCreate, UserUpdate

# --- UserCreate ---


def test_user_create_valid():
    u = UserCreate(
        email="trainer@example.com",
        role=UserRole.TRAINER,
        password="securepass1",
    )
    assert u.email == "trainer@example.com"
    assert u.role == UserRole.TRAINER


def test_user_create_password_too_short():
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", role=UserRole.PARTICIPANT, password="short")


def test_user_create_password_too_long():
    with pytest.raises(ValidationError):
        UserCreate(
            email="a@example.com",
            role=UserRole.PARTICIPANT,
            password="x" * 129,
        )


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="notanemail", role=UserRole.PARTICIPANT, password="password1")


def test_user_create_first_name_too_long():
    with pytest.raises(ValidationError):
        UserCreate(
            email="a@example.com",
            role=UserRole.PARTICIPANT,
            password="password1",
            first_name="A" * 101,
        )


def test_user_create_optional_names_default_none():
    u = UserCreate(email="a@example.com", role=UserRole.TRAINER, password="password1")
    assert u.first_name is None
    assert u.last_name is None


# --- UserUpdate ---


def test_user_update_all_optional():
    u = UserUpdate()
    assert u.email is None
    assert u.first_name is None
    assert u.role is None
    assert u.is_active is None


def test_user_update_partial_role():
    u = UserUpdate(role=UserRole.TRAINER)
    assert u.role == UserRole.TRAINER
    assert u.email is None


def test_user_update_partial_active():
    u = UserUpdate(is_active=False)
    assert u.is_active is False


def test_user_update_invalid_email():
    with pytest.raises(ValidationError):
        UserUpdate(email="bad-email")


def test_user_update_last_name_too_long():
    with pytest.raises(ValidationError):
        UserUpdate(last_name="B" * 101)


# --- InviteUserRequest ---


def test_invite_user_valid():
    req = InviteUserRequest(email="invite@example.com")
    assert req.email == "invite@example.com"


def test_invite_user_default_role_is_participant():
    req = InviteUserRequest(email="invite@example.com")
    assert req.role == UserRole.PARTICIPANT


def test_invite_user_invalid_email():
    with pytest.raises(ValidationError):
        InviteUserRequest(email="notvalid")


def test_invite_user_with_role():
    req = InviteUserRequest(email="trainer@example.com", role=UserRole.TRAINER)
    assert req.role == UserRole.TRAINER
