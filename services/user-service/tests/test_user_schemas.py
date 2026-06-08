import pytest
from pydantic import ValidationError

from src.models.user import UserRole
from src.schemas.user_schema import InviteUserRequest, UserCreate, UserUpdate


class TestUserCreate:
    def test_valid_trainer(self):
        user = UserCreate(email="trainer@example.com", role=UserRole.TRAINER, password="securepassword")
        assert user.email == "trainer@example.com"
        assert user.role == UserRole.TRAINER

    def test_valid_participant(self):
        user = UserCreate(email="p@example.com", role=UserRole.PARTICIPANT, password="securepassword")
        assert user.role == UserRole.PARTICIPANT

    @pytest.mark.parametrize(
        "password",
        ["short", "1234567", "x" * 129],
    )
    def test_password_length_rejected(self, password):
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com", role=UserRole.PARTICIPANT, password=password)

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="bad-email", role=UserRole.PARTICIPANT, password="goodpassword")

    def test_first_name_max_length_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="u@example.com",
                role=UserRole.PARTICIPANT,
                password="goodpassword",
                first_name="A" * 101,
            )

    def test_optional_names_default_none(self):
        user = UserCreate(email="u@example.com", role=UserRole.PARTICIPANT, password="goodpassword")
        assert user.first_name is None
        assert user.last_name is None


class TestUserUpdate:
    def test_all_fields_optional(self):
        update = UserUpdate()
        assert update.email is None
        assert update.role is None
        assert update.is_active is None
        assert update.first_name is None

    def test_partial_first_name_update(self):
        update = UserUpdate(first_name="Alice")
        assert update.first_name == "Alice"
        assert update.last_name is None

    def test_deactivate_user(self):
        update = UserUpdate(is_active=False)
        assert update.is_active is False

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserUpdate(email="not-an-email")


class TestInviteUserRequest:
    def test_default_role_is_participant(self):
        req = InviteUserRequest(email="invite@example.com")
        assert req.role == UserRole.PARTICIPANT

    def test_trainer_invite(self):
        req = InviteUserRequest(email="trainer@example.com", role=UserRole.TRAINER)
        assert req.role == UserRole.TRAINER

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            InviteUserRequest(email="bad")
