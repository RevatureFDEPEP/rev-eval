import pytest
from sqlalchemy.exc import IntegrityError
from src.models.user import User, UserRole


class TestUserRole:
    @pytest.mark.parametrize("role,expected", [
        (UserRole.TRAINER, "TRAINER"),
        (UserRole.PARTICIPANT, "PARTICIPANT"),
    ])
    def test_enum_string_values(self, role, expected):
        assert role == expected

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_all_roles_are_str_subclass(self, role):
        assert isinstance(role, str)

    def test_role_count(self):
        assert len(UserRole) == 2


class TestUserModel:
    def test_create_minimal_user(self, db):
        user = User(email="test@example.com", role=UserRole.PARTICIPANT)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None
        assert user.email == "test@example.com"

    def test_is_active_defaults_true(self, db):
        user = User(email="active@example.com", role=UserRole.TRAINER)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.is_active is True

    def test_optional_fields_default_none(self, db):
        user = User(email="minimal@example.com", role=UserRole.PARTICIPANT)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.full_name is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.password_hash is None
        assert user.organization_id is None
        assert user.last_login is None

    def test_created_at_auto_set(self, db):
        user = User(email="ts@example.com", role=UserRole.PARTICIPANT)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.created_at is not None

    def test_email_unique_constraint(self, db):
        db.add(User(email="dup@example.com", role=UserRole.PARTICIPANT))
        db.commit()
        db.add(User(email="dup@example.com", role=UserRole.TRAINER))
        with pytest.raises(IntegrityError):
            db.commit()

    @pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
    def test_both_roles_persist(self, db, role):
        user = User(email=f"{role.lower()}@example.com", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.role == role

    def test_full_name_stored(self, db):
        user = User(email="full@example.com", role=UserRole.PARTICIPANT, full_name="Jane Doe")
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.full_name == "Jane Doe"
