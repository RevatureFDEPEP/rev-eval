import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.init_db import Base
from src.models.user import User, UserRole
from src.schemas.auth_schema import RegisterRequest


@pytest.mark.parametrize(
    "password,should_pass",
    [
        ("short1", False),  # 6 chars – below the 8-char minimum
        ("1234567", False),  # 7 chars – one under the minimum
        ("exactly8", True),  # exactly 8 chars
        ("Secure#99!", True),  # strong password well above minimum
    ],
)
def test_register_request_enforces_minimum_password_length(password, should_pass):
    if should_pass:
        req = RegisterRequest(email="user@test.com", password=password)
        assert req.password == password
    else:
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", password=password)


def test_user_model_persists_with_auto_assigned_id_in_sqlite():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            email="trainer@corp.com",
            role=UserRole.TRAINER,
            full_name="Jane Doe",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
        user_email = user.email
        user_role = user.role
    assert user_id is not None and user_id > 0
    assert user_email == "trainer@corp.com"
    assert user_role == UserRole.TRAINER
