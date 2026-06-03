import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Settings are created during import, so test env vars must exist first.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "eval_ai_test")

# Ensure pytest can import modules from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import main first to follow the service's normal application import order.
# This avoids triggering the user model/session circular import from schema tests.
import main  # noqa: F401

from src.schemas.auth_schema import LoginRequest, RegisterRequest
from src.schemas.user_schema import InviteUserRequest, UserCreate


def test_login_request_accepts_valid_email_and_password():
    login_request = LoginRequest(
        email="participant@example.com",
        password="Password123!",
    )

    assert login_request.email == "participant@example.com"
    assert login_request.password == "Password123!"


@pytest.mark.parametrize(
    "invalid_email",
    [
        "",
        "not-an-email",
        "participant@",
    ],
)
def test_login_request_rejects_invalid_email(invalid_email):
    with pytest.raises(ValidationError):
        LoginRequest(
            email=invalid_email,
            password="Password123!",
        )


def test_register_request_defaults_to_participant_role():
    register_request = RegisterRequest(
        email="new.user@example.com",
        password="Password123!",
        full_name="New User",
    )

    assert register_request.email == "new.user@example.com"
    assert register_request.full_name == "New User"
    assert register_request.role.value == "PARTICIPANT"


def test_register_request_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="new.user@example.com",
            password="short",
        )


def test_user_create_accepts_valid_trainer_payload():
    user_create = UserCreate(
        email="trainer@example.com",
        first_name="Test",
        last_name="Trainer",
        role="TRAINER",
        password="Password123!",
    )

    assert user_create.email == "trainer@example.com"
    assert user_create.role.value == "TRAINER"
    assert user_create.first_name == "Test"
    assert user_create.last_name == "Trainer"


def test_invite_user_request_defaults_to_participant_role():
    invite_request = InviteUserRequest(
        email="invitee@example.com",
        first_name="Invited",
        last_name="User",
    )

    assert invite_request.email == "invitee@example.com"
    assert invite_request.role.value == "PARTICIPANT"
