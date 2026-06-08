"""Model + schema tests for user-service.

The User model is persisted via the hermetic in-memory `db_session` fixture
(conftest.py) — no Postgres. The user repository is an empty stub, so these
exercise the model and its constraints directly, plus parametrized schema
validation for the user/auth request models.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from src.models.user import User, UserRole
from src.schemas.user_schema import UserCreate


def _user(email="a@b.com", role=UserRole.PARTICIPANT, **kw) -> User:
    return User(email=email, role=role, password_hash="x", **kw)


def test_persist_and_read_back(db_session):
    db_session.add(_user(email="trainer@x.io", role=UserRole.TRAINER, full_name="Tina"))
    db_session.commit()

    row = db_session.query(User).filter_by(email="trainer@x.io").one()
    assert row.id is not None
    assert row.role == UserRole.TRAINER
    assert row.full_name == "Tina"


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


# --- schema validation (no DB) ---


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(email="a@b.com", role=UserRole.PARTICIPANT, password="longenough1"),
        dict(email="first.last@example.io", role=UserRole.TRAINER, password="anotherone"),
    ],
)
def test_user_create_valid(kwargs):
    model = UserCreate(**kwargs)
    assert model.email == kwargs["email"]


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(email="not-an-email", role=UserRole.PARTICIPANT, password="longenough1"),
        dict(email="a@b.com", role=UserRole.PARTICIPANT, password="short"),  # < 8 chars
        dict(email="a@b.com", password="longenough1"),  # role required
    ],
)
def test_user_create_invalid(kwargs):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserCreate(**kwargs)
