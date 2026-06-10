import os

# Must be set before any service module is imported.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Preload session module so Base and User are registered in the correct order
# (session.py re-exports Base and imports User — must load before tests import models).
import src.db.session  # noqa: E402,F401

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture
def db_session():
    """Hermetic sync session backed by in-memory SQLite.

    Builds a test-local engine (not the module-global one bound to DATABASE_URL).
    """
    from src.db.init_db import Base
    from src.models.user import User  # noqa: F401

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
