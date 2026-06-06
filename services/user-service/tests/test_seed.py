"""Unit tests for demo-user seeding (src/db/seed.py).

No DB required — SessionLocal is patched with a mock session. These cover
the idempotency guard, the insert path, and the never-block-startup
error handling.
"""
from unittest.mock import MagicMock, patch

from src.db.seed import DEMO_USERS, seed_users
from src.models.user import UserRole


def _mock_session(user_count: int) -> MagicMock:
    db = MagicMock()
    db.query.return_value.count.return_value = user_count
    return db


@patch("src.db.seed.SessionLocal")
def test_seed_skips_when_users_exist(mock_session_local):
    db = _mock_session(user_count=3)
    mock_session_local.return_value = db

    assert seed_users() == 0

    db.add_all.assert_not_called()
    db.commit.assert_not_called()
    db.close.assert_called_once()


@patch("src.db.seed.SessionLocal")
def test_seed_inserts_demo_users_on_empty_table(mock_session_local):
    db = _mock_session(user_count=0)
    mock_session_local.return_value = db

    assert seed_users() == len(DEMO_USERS)

    db.add_all.assert_called_once()
    db.commit.assert_called_once()
    db.close.assert_called_once()
    # The seeded set must include at least one trainer — the
    # test-management-service seed migration depends on it.
    users = list(db.add_all.call_args.args[0])
    assert len(users) == len(DEMO_USERS)
    assert any(u.role == UserRole.TRAINER for u in users)
    assert all(u.password_hash for u in users)


@patch("src.db.seed.SessionLocal")
def test_seed_failure_rolls_back_and_does_not_raise(mock_session_local):
    db = _mock_session(user_count=0)
    db.commit.side_effect = RuntimeError("db down")
    mock_session_local.return_value = db

    assert seed_users() == 0  # swallowed — startup must not be blocked

    db.rollback.assert_called_once()
    db.close.assert_called_once()
