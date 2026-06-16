import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpassword")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.db.session import Base
from src.models.quiz_session import QuizSession, SessionStatus
from src.models.skill import Skill  # noqa: F401
from src.models.test import Test  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401
from src.schemas.quiz_session_schema import QuizQuestionOut, SessionCreate, SessionRead

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def seeded_test(db: AsyncSession):
    test = Test(name="Python Basics", test_type="QUIZ", number_of_questions=5)
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestQuizSessionModel:
    @pytest.mark.asyncio
    async def test_defaults(self, db: AsyncSession, seeded_test: Test):
        now = datetime.utcnow()
        session = QuizSession(
            session_token="tok123",
            test_id=seeded_test.id,
            user_id=42,
            question_ids=["id1", "id2"],
            server_now=now,
            expires_at=now + timedelta(hours=1),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        assert session.id is not None
        assert len(session.id) == 36  # UUID string format
        assert session.current_index == 0
        assert session.status == SessionStatus.STARTED
        assert session.submitted_at is None

    @pytest.mark.asyncio
    async def test_question_ids_persisted(self, db: AsyncSession, seeded_test: Test):
        now = datetime.utcnow()
        q_ids = ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
        session = QuizSession(
            session_token="tok456",
            test_id=seeded_test.id,
            user_id=1,
            question_ids=q_ids,
            server_now=now,
            expires_at=now + timedelta(hours=1),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        assert session.question_ids == q_ids

    @pytest.mark.asyncio
    async def test_unique_session_token(self, db: AsyncSession, seeded_test: Test):
        now = datetime.utcnow()
        s1 = QuizSession(
            session_token="same-token",
            test_id=seeded_test.id,
            user_id=1,
            question_ids=["id1"],
            server_now=now,
            expires_at=now + timedelta(hours=1),
        )
        s2 = QuizSession(
            session_token="same-token",
            test_id=seeded_test.id,
            user_id=2,
            question_ids=["id2"],
            server_now=now,
            expires_at=now + timedelta(hours=1),
        )
        db.add(s1)
        await db.commit()
        db.add(s2)
        with pytest.raises(Exception):  # noqa: B017 — IntegrityError from SQLite unique constraint
            await db.commit()

    @pytest.mark.parametrize("status", list(SessionStatus))
    def test_status_enum_values(self, status: SessionStatus):
        assert isinstance(status.value, str)
        assert status.value in ("STARTED", "IN_PROGRESS", "SUBMITTED", "EXPIRED")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSessionSchemas:
    def test_session_create_requires_test_id(self):
        with pytest.raises((ValidationError, TypeError)):
            SessionCreate()

    def test_session_create_valid_minimal(self):
        s = SessionCreate(test_id=1)
        assert s.test_id == 1
        assert s.submission_id is None

    def test_session_create_with_submission_id(self):
        s = SessionCreate(test_id=5, submission_id=10)
        assert s.submission_id == 10

    def test_quiz_question_out_no_correct_answers_field(self):
        q = QuizQuestionOut(
            question_id="abc123",
            question_text="What is Python?",
            question_type="mcq",
            difficulty="easy",
            options=[{"option_id": 1, "text": "A language"}],
        )
        data = q.model_dump()
        assert "correct_answers" not in data
        assert data["question_id"] == "abc123"

    def test_session_read_serializes(self):
        now = datetime.utcnow()
        r = SessionRead(
            session_id="some-uuid",
            session_token="tok",
            test_id=1,
            user_id=42,
            status="STARTED",
            current_index=0,
            server_now=now,
            expires_at=now + timedelta(hours=1),
            first_question=None,
        )
        assert r.current_index == 0
        assert r.first_question is None
