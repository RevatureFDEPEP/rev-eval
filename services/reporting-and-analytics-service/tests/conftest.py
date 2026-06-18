import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")
os.environ.setdefault("DB_NAME", "reporting")
os.environ.setdefault("EVAL_AI_DB_NAME", "eval_ai_dev")

import pytest
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.db.session import EvalAiBase, get_eval_ai_db
from src.models.quiz_session import QuizSession, SessionStatus  # noqa: F401
from src.models.session_answer import SessionAnswer  # noqa: F401
from starlette.testclient import TestClient


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EvalAiBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    EvalAiBase.metadata.drop_all(engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_eval_ai_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
