import os
import sys
from pathlib import Path

# Settings are created during import, so test env vars must exist first.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "eval_ai_test")
os.environ.setdefault("ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

# Ensure pytest can import modules from the service root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta  # noqa: E402

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """An AsyncSession bound to a fresh in-memory SQLite DB with all tables.

    The quiz models use portable column types (String uuid + generic JSON), so
    the same schema that runs on Postgres in production builds here unmodified —
    giving real integration coverage of the repository/service layer without a
    live database.
    """
    # Register every model on Base before create_all.
    import src.models.quiz_session  # noqa: F401
    import src.models.skill  # noqa: F401
    import src.models.test  # noqa: F401
    import src.models.test_skill  # noqa: F401
    import src.models.test_submission  # noqa: F401
    from src.db.session import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as session:
            yield session
    finally:
        await engine.dispose()


async def make_test(session, *, number_of_questions=3, active=True, minutes=30):
    """Insert and return a Test row for quiz-session tests."""
    from src.models.test import Test, TestType

    test = Test(
        name="Sample Quiz",
        test_type=TestType.QUIZ,
        active=active,
        number_of_questions=number_of_questions,
        duration=timedelta(minutes=minutes),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(test)
    await session.commit()
    await session.refresh(test)
    return test


def sample_question_pool():
    """A deterministic mixed-type pool, each with answer keys (server-only)."""
    return [
        {
            "_id": "q-mcq",
            "type": "mcq",
            "question_text": "Pick the second option.",
            "options": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
            "correct_answers": [2],
            "answer_explanation": "b is correct",
        },
        {
            "_id": "q-tf",
            "type": "true_false",
            "question_text": "The sky is blue.",
            "correct_answers": [True],
        },
        {
            "_id": "q-multi",
            "type": "multi",
            "question_text": "Pick options 1 and 2.",
            "options": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
            "correct_answers": [1, 2],
        },
    ]
