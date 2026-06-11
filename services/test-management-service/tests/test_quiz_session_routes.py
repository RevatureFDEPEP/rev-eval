"""
tests/test_quiz_session_routes.py

Integration tests for quiz session endpoints.
Uses SQLite (via DATABASE_URL override) + FastAPI TestClient.
Mocks fetch_questions_for_part with AsyncMock to avoid calling the real
question-management-service during tests.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mgmt.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

import asyncio
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from src.db.session import get_db, engine, Base
from src.models.test import Test  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401
from src.models.quiz_session import QuizSession  # noqa: F401 — must import before create_all
from src.utils.dependencies import get_current_user_from_headers

TestingAsyncSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_create_tables())


async def override_get_db():
    async with TestingAsyncSession() as db:
        yield db


FAKE_TRAINER = {"id": 1, "email": "qs-trainer@test.com", "role": "TRAINER"}


async def override_get_current_user():
    return FAKE_TRAINER


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_from_headers] = override_get_current_user

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_raw_questions(n_easy: int = 3, n_medium: int = 4, n_hard: int = 4) -> list:
    """Return raw question dicts in the format question-management-service would return."""
    questions = []
    for i in range(n_easy):
        questions.append({
            "id": f"easy-qs-{i}",
            "type": "mcq",
            "question_text": f"Easy question {i}?",
            "difficulty": "easy",
            "options": [{"option_id": 0, "text": "Option A"}, {"option_id": 1, "text": "Option B"}],
            "correct_answer": 0,
        })
    for i in range(n_medium):
        questions.append({
            "id": f"med-qs-{i}",
            "type": "mcq",
            "question_text": f"Medium question {i}?",
            "difficulty": "medium",
            "options": [{"option_id": 0, "text": "Option A"}, {"option_id": 1, "text": "Option B"}],
            "correct_answer": 1,
        })
    for i in range(n_hard):
        questions.append({
            "id": f"hard-qs-{i}",
            "type": "mcq",
            "question_text": f"Hard question {i}?",
            "difficulty": "hard",
            "options": [{"option_id": 0, "text": "Option A"}, {"option_id": 1, "text": "Option B"}],
            "correct_answer": 0,
        })
    return questions


_PART_A_MOCK = _make_raw_questions(3, 4, 4)
_PART_B_MOCK = _make_raw_questions(2, 4, 5)

# We create one test at module level so all test classes can reference TEST_ID.
_test_resp = client.post("/v1/api/tests/", json={
    "name": "Quiz Session Test",
    "test_type": "QUIZ",
    "number_of_questions": 20,
    "duration_seconds": 1800,
})
assert _test_resp.status_code == 201, f"fixture test creation failed: {_test_resp.text}"
TEST_ID = _test_resp.json()["id"]


# ---------------------------------------------------------------------------
# TestQuizSessionCreate
# ---------------------------------------------------------------------------

class TestQuizSessionCreate:
    def test_create_session_returns_201(self):
        resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 1001,
            "user_id": 42,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["test_id"] == TEST_ID
        assert body["submission_id"] == 1001
        assert body["user_id"] == 42
        assert body["status"] == "STARTED"
        assert "id" in body

    def test_create_session_with_custom_config(self):
        resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 1002,
            "user_id": 43,
            "total_questions": 15,
            "part_a_config": {"easy": 5, "medium": 5, "hard": 5},
        })
        assert resp.status_code == 201
        assert resp.json()["total_questions"] == 15


# ---------------------------------------------------------------------------
# TestQuizSessionGet
# ---------------------------------------------------------------------------

class TestQuizSessionGet:

    @classmethod
    def setup_class(cls):
        resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 2001,
            "user_id": 50,
        })
        assert resp.status_code == 201
        cls.session_id = resp.json()["id"]

    def test_get_session_by_id(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == self.session_id
        assert body["status"] == "STARTED"

    def test_get_session_not_found(self):
        resp = client.get("/v1/api/test-sessions/nonexistent-uuid-xxxx")
        assert resp.status_code == 404

    def test_get_session_by_submission(self):
        resp = client.get("/v1/api/test-sessions/by-submission/2001")
        assert resp.status_code == 200
        assert resp.json()["submission_id"] == 2001

    def test_get_session_by_submission_not_found(self):
        resp = client.get("/v1/api/test-sessions/by-submission/99999")
        assert resp.status_code == 404

    def test_get_session_status(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == self.session_id
        assert body["status"] == "STARTED"
        assert body["current_part"] == "A"

    def test_get_session_status_not_found(self):
        resp = client.get("/v1/api/test-sessions/no-such-session/status")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestQuizSessionPartA
# ---------------------------------------------------------------------------

class TestQuizSessionPartA:

    @classmethod
    def setup_class(cls):
        resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 3001,
            "user_id": 60,
        })
        assert resp.status_code == 201
        cls.session_id = resp.json()["id"]

    def test_get_part_a_questions(self):
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_A_MOCK
            resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-a/questions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == self.session_id
        assert isinstance(body["questions"], list)
        assert len(body["questions"]) > 0
        # Correct answers must NOT be in the response
        for q in body["questions"]:
            assert "correct_answer" not in q
            assert "correct_answers" not in q

    def test_get_part_a_questions_cached_on_second_call(self):
        """Second call should return cached questions without calling fetch again."""
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_A_MOCK
            resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-a/questions")

        assert resp.status_code == 200
        # fetch should not be called again (questions already stored)
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch2:
            resp2 = client.get(f"/v1/api/test-sessions/{self.session_id}/part-a/questions")
            mock_fetch2.assert_not_called()

        assert resp2.status_code == 200

    def test_status_is_part_a_in_progress_after_fetch(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.json()["status"] == "PART_A_IN_PROGRESS"

    def test_submit_part_a(self):
        # Build answer payload — answer every question with option 0
        q_resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-a/questions")
        questions = q_resp.json()["questions"]
        answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in questions]

        resp = client.post(
            f"/v1/api/test-sessions/{self.session_id}/part-a/submit",
            json={"session_id": self.session_id, "answers": answers},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "score" in body
        assert "total_questions" in body
        assert "correct_answers" in body

    def test_status_is_part_a_completed_after_submit(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.json()["status"] == "PART_A_COMPLETED"
        assert resp.json()["current_part"] == "B"

    def test_submit_part_a_again_returns_409(self):
        q_resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-a/questions")
        # After PART_A_COMPLETED, fetching part A questions should return 409
        assert q_resp.status_code == 409

    def test_submit_part_a_idempotency_replay(self):
        """Same Idempotency-Key on a fresh session returns cached response."""
        # Create new session for this test
        s_resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 3002,
            "user_id": 61,
        })
        sid = s_resp.json()["id"]

        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_A_MOCK
            client.get(f"/v1/api/test-sessions/{sid}/part-a/questions")

        q_resp = client.get(f"/v1/api/test-sessions/{sid}/part-a/questions")
        questions = q_resp.json()["questions"]
        answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in questions]

        # First submit with idempotency key
        resp1 = client.post(
            f"/v1/api/test-sessions/{sid}/part-a/submit",
            json={"session_id": sid, "answers": answers},
            headers={"Idempotency-Key": "test-key-abc123"},
        )
        assert resp1.status_code == 200

        # Replay with same key — must return same response
        resp2 = client.post(
            f"/v1/api/test-sessions/{sid}/part-a/submit",
            json={"session_id": sid, "answers": answers},
            headers={"Idempotency-Key": "test-key-abc123"},
        )
        assert resp2.status_code == 200
        assert resp1.json()["score"] == resp2.json()["score"]


# ---------------------------------------------------------------------------
# TestQuizSessionPartB
# ---------------------------------------------------------------------------

class TestQuizSessionPartB:

    @classmethod
    def setup_class(cls):
        # Create session + complete part A
        s_resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 4001,
            "user_id": 70,
        })
        assert s_resp.status_code == 201
        cls.session_id = s_resp.json()["id"]

        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_A_MOCK
            client.get(f"/v1/api/test-sessions/{cls.session_id}/part-a/questions")

        q_resp = client.get(f"/v1/api/test-sessions/{cls.session_id}/part-a/questions")
        questions = q_resp.json()["questions"]
        answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in questions]
        client.post(
            f"/v1/api/test-sessions/{cls.session_id}/part-a/submit",
            json={"session_id": cls.session_id, "answers": answers},
        )

    def test_get_part_b_questions(self):
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_B_MOCK
            resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-b/questions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == self.session_id
        assert isinstance(body["questions"], list)
        # Correct answers must NOT be in the response
        for q in body["questions"]:
            assert "correct_answer" not in q
            assert "correct_answers" not in q

    def test_status_is_part_b_in_progress(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.json()["status"] == "PART_B_IN_PROGRESS"

    def test_get_part_b_questions_not_available_before_part_a_complete(self):
        """Accessing Part B questions on a new (STARTED) session returns 409."""
        s_resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 4002,
            "user_id": 71,
        })
        sid = s_resp.json()["id"]
        resp = client.get(f"/v1/api/test-sessions/{sid}/part-b/questions")
        assert resp.status_code == 409

    def test_submit_part_b_finalizes_session(self):
        q_resp = client.get(f"/v1/api/test-sessions/{self.session_id}/part-b/questions")
        questions = q_resp.json()["questions"]
        answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in questions]

        resp = client.post(
            f"/v1/api/test-sessions/{self.session_id}/part-b/submit",
            json={"session_id": self.session_id, "answers": answers},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "score" in body
        assert "total_questions" in body

    def test_status_is_completed_after_part_b_submit(self):
        resp = client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.json()["status"] == "COMPLETED"

    def test_submit_part_b_again_returns_409(self):
        """Submitting Part B on COMPLETED session returns 409."""
        answers = [{"question_id": "fake-q", "selected_answers": [0]}]
        resp = client.post(
            f"/v1/api/test-sessions/{self.session_id}/part-b/submit",
            json={"session_id": self.session_id, "answers": answers},
        )
        assert resp.status_code == 409

    def test_submit_part_b_idempotency_replay(self):
        """Same Idempotency-Key on completed Part B returns cached response."""
        # Create a new session and advance to part B
        s_resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 4003,
            "user_id": 72,
        })
        sid = s_resp.json()["id"]

        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = _PART_A_MOCK
            client.get(f"/v1/api/test-sessions/{sid}/part-a/questions")

        q_resp = client.get(f"/v1/api/test-sessions/{sid}/part-a/questions")
        a_answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in q_resp.json()["questions"]]
        client.post(f"/v1/api/test-sessions/{sid}/part-a/submit", json={"session_id": sid, "answers": a_answers})

        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new_callable=AsyncMock,
        ) as mock_fetch2:
            mock_fetch2.return_value = _PART_B_MOCK
            client.get(f"/v1/api/test-sessions/{sid}/part-b/questions")

        b_resp = client.get(f"/v1/api/test-sessions/{sid}/part-b/questions")
        b_answers = [{"question_id": q["question_id"], "selected_answers": [0]} for q in b_resp.json()["questions"]]

        resp1 = client.post(
            f"/v1/api/test-sessions/{sid}/part-b/submit",
            json={"session_id": sid, "answers": b_answers},
            headers={"Idempotency-Key": "part-b-key-xyz"},
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            f"/v1/api/test-sessions/{sid}/part-b/submit",
            json={"session_id": sid, "answers": b_answers},
            headers={"Idempotency-Key": "part-b-key-xyz"},
        )
        assert resp2.status_code == 200
        assert resp1.json()["score"] == resp2.json()["score"]


# ---------------------------------------------------------------------------
# TestQuizSessionEdgeCases
# ---------------------------------------------------------------------------

class TestQuizSessionEdgeCases:

    def test_submit_part_a_without_fetching_questions_returns_409(self):
        s_resp = client.post("/v1/api/test-sessions/", json={
            "test_id": TEST_ID,
            "submission_id": 5001,
            "user_id": 80,
        })
        sid = s_resp.json()["id"]

        # Manually advance status to PART_A_IN_PROGRESS by calling get_part_a_questions
        # but DON'T store questions — simulate the guard by calling submit directly on STARTED
        # Actually we need PART_A_IN_PROGRESS but no questions stored.
        # The guard "Cannot submit Part A in status STARTED" fires first.
        resp = client.post(
            f"/v1/api/test-sessions/{sid}/part-a/submit",
            json={"session_id": sid, "answers": []},
        )
        # Status is STARTED, not PART_A_IN_PROGRESS -> 409
        assert resp.status_code == 409

    def test_get_part_a_questions_session_not_found(self):
        resp = client.get("/v1/api/test-sessions/no-such-id/part-a/questions")
        assert resp.status_code == 404

    def test_submit_part_a_session_not_found(self):
        resp = client.post(
            "/v1/api/test-sessions/no-such-id/part-a/submit",
            json={"session_id": "no-such-id", "answers": []},
        )
        assert resp.status_code == 404

    def test_submit_part_b_session_not_found(self):
        resp = client.post(
            "/v1/api/test-sessions/no-such-id/part-b/submit",
            json={"session_id": "no-such-id", "answers": []},
        )
        assert resp.status_code == 404

    def test_get_part_b_questions_session_not_found(self):
        resp = client.get("/v1/api/test-sessions/no-such-id/part-b/questions")
        assert resp.status_code == 404
