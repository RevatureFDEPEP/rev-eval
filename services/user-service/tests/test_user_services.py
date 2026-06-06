from datetime import datetime
from unittest.mock import MagicMock, patch

from src.models.user import User, UserRole
from src.services.auth_service import AuthService
from src.services.user_service import UserService


class FakeDb:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 10
        self.refreshed.append(obj)


def user(**overrides):
    data = {
        "id": 1,
        "email": "participant@example.com",
        "password_hash": "hashed",
        "full_name": "Pat Participant",
        "first_name": "Pat",
        "last_name": "Participant",
        "role": UserRole.PARTICIPANT,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    data.update(overrides)
    return User(**data)


def test_password_and_token_helpers_round_trip():
    hashed = AuthService.hash_password("Password123!")

    assert AuthService.verify_password("Password123!", hashed)
    assert not AuthService.verify_password("Password123!", "")

    token = AuthService.create_access_token({"sub": "1", "email": "a@example.com"})
    payload = AuthService.decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["email"] == "a@example.com"


def test_authenticate_user_rejects_missing_inactive_or_bad_password():
    db = object()
    inactive = user(is_active=False)
    active = user(is_active=True)

    with patch.object(AuthService, "get_user_by_email", return_value=None):
        assert AuthService.authenticate_user(db, "missing@example.com", "pw") is None

    with patch.object(AuthService, "get_user_by_email", return_value=inactive):
        assert AuthService.authenticate_user(db, inactive.email, "pw") is None

    with (
        patch.object(AuthService, "get_user_by_email", return_value=active),
        patch.object(AuthService, "verify_password", return_value=False),
    ):
        assert AuthService.authenticate_user(db, active.email, "wrong") is None


def test_authenticate_user_updates_last_login_on_success():
    db = FakeDb()
    active = user(is_active=True)

    with (
        patch.object(AuthService, "get_user_by_email", return_value=active),
        patch.object(AuthService, "verify_password", return_value=True),
    ):
        result = AuthService.authenticate_user(db, active.email, "Password123!")

    assert result == active
    assert active.last_login is not None
    assert db.commits == 1
    assert db.refreshed == [active]


def test_create_user_splits_full_name_and_persists():
    db = FakeDb()

    with patch.object(AuthService, "hash_password", return_value="hashed"):
        created = AuthService.create_user(
            db,
            "new@example.com",
            "Password123!",
            "New User",
            UserRole.TRAINER,
        )

    assert created.first_name == "New"
    assert created.last_name == "User"
    assert created.role == UserRole.TRAINER
    assert db.added == [created]
    assert db.commits == 1


def test_user_service_invite_returns_existing_user_without_creating():
    db = FakeDb()
    existing = user(id=5, email="existing@example.com")

    with patch.object(AuthService, "get_user_by_email", return_value=existing):
        result = UserService.invite_user(db, existing.email)

    assert result["id"] == 5
    assert result["invite_sent"] is False
    assert db.added == []


def test_user_service_invite_creates_inactive_user():
    db = FakeDb()

    with patch.object(AuthService, "get_user_by_email", return_value=None):
        result = UserService.invite_user(
            db,
            "invitee@example.com",
            first_name="Invited",
            last_name="User",
            role=UserRole.TRAINER,
        )

    created = db.added[0]
    assert created.is_active is False
    assert created.full_name == "Invited User"
    assert result["email"] == "invitee@example.com"
    assert result["id"] == 10


def test_user_service_list_users_applies_role_and_pagination():
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.offset.return_value = query
    query.all.return_value = ["user"]
    db = MagicMock()
    db.query.return_value = query

    result = UserService.list_users(
        db,
        role=UserRole.TRAINER,
        limit=5,
        offset=10,
    )

    assert result == ["user"]
    query.filter.assert_called_once()
    query.limit.assert_called_once_with(5)
    query.offset.assert_called_once_with(10)
