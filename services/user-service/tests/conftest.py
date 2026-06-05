import os

# Must be set before any src.* imports to satisfy pydantic-settings
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpassword")
os.environ.setdefault("DB_NAME", "testdb")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# session.py imports User (registering it with Base) via the correct load order.
# Importing init_db first would cause a circular import when user.py tries to
# re-import session.py before User is defined.
from src.db.session import Base


@pytest.fixture(scope="function")
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)
    e.dispose()


@pytest.fixture(scope="function")
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()
