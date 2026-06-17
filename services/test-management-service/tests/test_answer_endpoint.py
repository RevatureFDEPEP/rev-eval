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
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from src.db.session import Base, get_db
from src.models.idempotency_key import IdempotencyKey  # noqa: F401
from src.models.quiz_session import QuizSession, SessionStatus
from src.models.session_answer import SessionAnswer  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test import Test  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import SubmissionStatus, TestSubmission  # noqa: F401
from src.utils.dependencies import get_current_user_from_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MCQ_QUESTION = {
    "_id": "qid1",
    "question_text": "What is Python?",
    "type": "mcq",
    "difficulty": "easy",
    "options": [{"option_id": 1, "text": "A language"}, {"option_id": 2, "text": "A snake"}],
    "correct_answers": [1],
}

MCQ_QUESTION_2 = {
    "_id": "qid2",
    "question_text": "What is a list?",
    "type": "mcq",
    "difficulty": "easy",
    "options": [{"option_id": 1, "text": "A collection"}, {"option_id": 2, "text": "A dict"}],
    "correct_answers": [1],
}

TEXT_QUESTION = {
    "_id": "qid1",
    "question_text": "Explain Python.",
    "type": "text",
    "difficulty": "medium",
    "options": None,
    "correct_answers": None,
}

FAKE_USER = {"id": 1, "email": "test@example.com", "role": "PARTICIPANT"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_client():
    """In-memory SQLite db + FastAPI test client with dep overrides."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionFactory() as db:
        async def override_get_db():
            yield db

        async def override_get_user():
            return FAKE_USER

        from main import app

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_from_headers] = override_get_user

        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield db, client

        app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _seed_session(
    db: AsyncSession,
    question_ids: list[str],
    *,
    with_submission: bool = False,
    status: SessionStatus = SessionStatus.STARTED,
) -> tuple[QuizSession, TestSubmission | None]:
    test = Test(name="Test Quiz", test_type="QUIZ", number_of_questions=len(question_ids))
    db.add(test)
    await db.flush()

    submission = None
    if with_submission:
        submission = TestSubmission(
            test_id=test.id,
            user_id=FAKE_USER["id"],
            status=SubmissionStatus.IN_PROGRESS,
        )
        db.add(submission)
        await db.flush()

    now = datetime.utcnow()
    session = QuizSession(
        session_token="tok-test-" + "_".join(question_ids),
        test_id=test.id,
        submission_id=submission.id if submission else None,
        user_id=FAKE_USER["id"],
        question_ids=question_ids,
        status=status,
        server_now=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(session)
    await db.flush()   # populates session.id before commit
    await db.commit()
    # No db.refresh() here — that would autobegin a new txn, blocking db.begin() in the route
    return session, submission


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAnswerEndpoint:
    @pytest.mark.asyncio
    async def test_normal_flow_not_last_question(self, db_client):
        db, client = db_client
        session, _ = await _seed_session(db, ["qid1", "qid2"])

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(side_effect=[MCQ_QUESTION, MCQ_QUESTION_2]),
        ):
            resp = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "qid1", "submitted_answers": [1]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 1.0
        assert data["algorithm"] == "exact_match"
        assert data["session_status"] == "IN_PROGRESS"
        assert data["current_index"] == 1
        assert data["next_question"] is not None
        assert data["next_question"]["question_id"] == "qid2"

    @pytest.mark.asyncio
    async def test_last_question_submits_session_and_updates_submission(self, db_client):
        db, client = db_client
        session, submission = await _seed_session(db, ["qid1"], with_submission=True)

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(return_value=MCQ_QUESTION),
        ):
            resp = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "qid1", "submitted_answers": [1]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["session_status"] == "SUBMITTED"
        assert data["next_question"] is None

        # Verify DB state
        await db.refresh(submission)
        assert submission.status == SubmissionStatus.COMPLETED
        assert submission.ai_score == 100

    @pytest.mark.asyncio
    async def test_already_submitted_session_returns_409(self, db_client):
        db, client = db_client
        session, _ = await _seed_session(db, ["qid1"], status=SessionStatus.SUBMITTED)

        resp = await client.post(
            f"/v1/api/sessions/{session.id}/answer",
            json={"question_id": "qid1", "submitted_answers": [1]},
        )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_wrong_question_id_returns_422(self, db_client):
        db, client = db_client
        session, _ = await _seed_session(db, ["qid1"])

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(return_value=MCQ_QUESTION),
        ):
            resp = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "wrong-id", "submitted_answers": [1]},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key_returns_cached_response(self, db_client):
        db, client = db_client
        session, _ = await _seed_session(db, ["qid1", "qid2"])
        idem_key = "unique-key-abc123"

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(side_effect=[MCQ_QUESTION, MCQ_QUESTION_2]),
        ):
            resp1 = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "qid1", "submitted_answers": [1]},
                headers={"Idempotency-Key": idem_key},
            )

        # Count session_answer rows after first call.
        # Must commit after the SELECT to close autobegin, otherwise the second
        # call's db.begin() raises "A transaction is already begun on this Session."
        result = await db.execute(select(SessionAnswer).where(SessionAnswer.session_id == session.id))
        rows_after_first = len(result.scalars().all())
        await db.commit()

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(side_effect=[MCQ_QUESTION, MCQ_QUESTION_2]),
        ):
            resp2 = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "qid1", "submitted_answers": [1]},
                headers={"Idempotency-Key": idem_key},
            )

        result = await db.execute(select(SessionAnswer).where(SessionAnswer.session_id == session.id))
        rows_after_second = len(result.scalars().all())

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()
        assert rows_after_second == rows_after_first  # no new row on duplicate

    @pytest.mark.asyncio
    async def test_text_question_score_is_null_and_index_advances(self, db_client):
        db, client = db_client
        session, _ = await _seed_session(db, ["qid1", "qid2"])

        with patch(
            "src.v1.routes.quiz_session_route.fetch_question",
            new=AsyncMock(side_effect=[TEXT_QUESTION, MCQ_QUESTION_2]),
        ):
            resp = await client.post(
                f"/v1/api/sessions/{session.id}/answer",
                json={"question_id": "qid1", "submitted_answers": ["some answer"]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] is None
        assert data["algorithm"] == "none"
        assert data["current_index"] == 1
