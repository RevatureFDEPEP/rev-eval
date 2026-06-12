"""
Repository tests for user-service using an in-memory SQLite database.

Creates a fresh SQLAlchemy engine per test module — completely isolated
from the production PostgreSQL engine defined in src/db/session.py.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.db.init_db import Base
from src.models.user import User, UserRole
from src.services.auth_service import AuthService


@pytest.fixture(scope="module")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_create_user_and_fetch_by_email(db):
    user = AuthService.create_user(db, "alice@example.com", "password123", "Alice Smith")
    assert user.id is not None
    fetched = AuthService.get_user_by_email(db, "alice@example.com")
    assert fetched is not None
    assert fetched.email == "alice@example.com"
    assert fetched.full_name == "Alice Smith"


def test_create_user_assigns_participant_role_by_default(db):
    user = AuthService.create_user(db, "bob@example.com", "password123")
    assert user.role == UserRole.PARTICIPANT


def test_create_user_with_trainer_role(db):
    user = AuthService.create_user(
        db, "carol@example.com", "password123", role=UserRole.TRAINER
    )
    assert user.role == UserRole.TRAINER


def test_get_user_by_id(db):
    user = AuthService.create_user(db, "dave@example.com", "password123")
    fetched = AuthService.get_user_by_id(db, user.id)
    assert fetched is not None
    assert fetched.id == user.id


def test_duplicate_email_raises_integrity_error(db):
    AuthService.create_user(db, "duplicate@example.com", "password123")
    with pytest.raises(IntegrityError):
        AuthService.create_user(db, "duplicate@example.com", "different123")
