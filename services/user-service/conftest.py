"""Test bootstrap for user-service.

`src.config.settings.Settings()` runs at import and requires DB_* + JWT_SECRET.
Set hermetic defaults here (imported before test collection) so importing the
service modules never touches a real database — the engine is created lazily
and these tests never open a connection.
"""
import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-0123456789abcdef-32b")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# src/db/session.py and src/models/user.py import each other (session re-exports
# Base and imports User to register it). It only resolves when session loads
# first — the order main.py uses. Preload it (import src.db.session below) so
# tests can import models in any order. Engine creation is lazy, so no DB
# connection is opened.
import pytest  # noqa: E402
import src.db.session  # noqa: E402,F401
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture
def db_session():
    """A hermetic sync SQLAlchemy session backed by in-memory SQLite.

    Builds a *test-local* engine (NOT the module-global ``src.db.session.engine``,
    which is bound to the env DATABASE_URL at import time) so the User model can
    be persisted and its constraints exercised without Postgres. ``StaticPool``
    + ``check_same_thread=False`` keep the single in-memory DB alive across the
    fixture. The user repository is an empty stub, so these tests target the
    model directly.
    """
    from src.db.init_db import Base
    from src.models.user import User  # noqa: F401  (register the table)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
