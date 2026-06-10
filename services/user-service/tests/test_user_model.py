"""Model + service tests for user-service against a hermetic in-memory DB.

Uses the sync `db_session` fixture from conftest.py (SQLite, no Postgres).
The user repository is an empty stub, so these test the User model directly
and exercise AuthService for the create/authenticate paths.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.user import User, UserRole
from src.services.auth_service import AuthService


def _user(email="test@example.com", role=UserRole.PARTICIPANT, **kw) -> User:
    return User(email=email, role=role, password_hash="hashed", **kw)


def test_persist_and_read_back(db_session):
    db_session.add(_user(email="trainer@x.io", role=UserRole.TRAINER, full_name="Tina Trainer"))
    db_session.commit()

    row = db_session.query(User).filter_by(email="trainer@x.io").one()
    assert row.id is not None
    assert row.role == UserRole.TRAINER
    assert row.full_name == "Tina Trainer"


def test_is_active_defaults_true(db_session):
    user = _user()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.is_active is True


def test_email_unique_constraint(db_session):
    db_session.add(_user(email="dup@x.io"))
    db_session.commit()
    db_session.add(_user(email="dup@x.io"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.PARTICIPANT])
def test_role_enum_persists(db_session, role):
    user = _user(email=f"{role.value.lower()}@x.io", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.role == role


def test_create_user_via_auth_service(db_session):
    user = AuthService.create_user(db_session, "newuser@x.io", "password123", "New User")
    assert user.id is not None
    assert user.email == "newuser@x.io"
    assert user.full_name == "New User"
    assert user.is_active is True
    assert user.password_hash != "password123"


def test_authenticate_user_correct_password(db_session):
    AuthService.create_user(db_session, "auth@x.io", "secret123")
    result = AuthService.authenticate_user(db_session, "auth@x.io", "secret123")
    assert result is not None
    assert result.email == "auth@x.io"


def test_authenticate_user_wrong_password(db_session):
    AuthService.create_user(db_session, "auth2@x.io", "correct")
    result = AuthService.authenticate_user(db_session, "auth2@x.io", "wrong")
    assert result is None
