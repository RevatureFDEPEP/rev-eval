"""
tests/test_integration_postgres.py

Full quiz-session lifecycle tested against a real Postgres instance.

Skipped locally (requires the CI Postgres service container).
Covers the gaps that SQLite cannot: UUID primary-key round-trips, JSON column
persistence, and SELECT FOR UPDATE serialization (see also test_session_lock_postgres.py).

Run condition: CI=true environment variable (set automatically by GitHub Actions).
"""

import asyncio
import os
from unittest.mock import patch

import pytest

# Set env vars BEFORE any src.* import so pydantic-settings doesn't blow up.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mgmt.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

_IN_CI = os.environ.get("CI") == "true"

# Skip the entire module when not in CI
pytestmark = pytest.mark.skipif(
    not _IN_CI,
    reason="Postgres integration tests require CI service container (CI=true)",
)

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from src.db.session import Base, get_db  # noqa: E402
from src.models.test import Test, TestType  # noqa: E402, F401
from src.models.skill import Skill  # noqa: E402, F401
from src.models.test_skill import TestSkill  # noqa: E402, F401
from src.models.test_submission import TestSubmission  # noqa: E402, F401
from src.models.quiz_session import QuizSession, SessionStatus  # noqa: E402, F401
from src.utils.dependencies import get_current_user_from_headers  # noqa: E402

_PG_URL = "postgresql+asyncpg://test:test@localhost:5432/test"

# Engine created at module level with NullPool so connections are made fresh
# in whichever event loop (TestClient's) calls them — no pool cross-loop issue.
_pg_engine = create_async_engine(_PG_URL, poolclass=NullPool)
_PgSession = sessionmaker(_pg_engine, class_=AsyncSession, expire_on_commit=False)

FAKE_TRAINER = {
    "id": 1,
    "email": "pg_trainer@test.com",
    "role": "TRAINER",
    "full_name": "PG Trainer",
}

_FAKE_QUESTIONS = [
    {
        "id": f"q{i}",
        "question_type": "mcq",
        "difficulty": d,
        "question_text": f"Postgres question {i}",
        "correct_answers": [1],
        "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
    }
    for i, d in enumerate(
        ["easy"] * 3 + ["medium"] * 4 + ["hard"] * 4, start=1
    )
]


async def _fake_fetch(question_service_url, test_id, config, exclude_ids):
    return _FAKE_QUESTIONS


async def _pg_get_db():
    async with _PgSession() as db:
        yield db


async def _fake_user():
    return FAKE_TRAINER


class TestQuizSessionLifecyclePostgres:
    """
    Happy-path quiz session lifecycle against real Postgres.

    Tests: create test → create submission → create session →
           get Part A questions → submit Part A →
           get Part B questions → submit Part B → assert COMPLETED.
    """

    @classmethod
    def setup_class(cls):
        # Bootstrap Postgres schema (idempotent create_all).
        async def _bootstrap():
            async with _pg_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(_bootstrap())

        # Save current overrides so teardown_class can restore them.
        cls._prev_db = app.dependency_overrides.get(get_db)
        cls._prev_user = app.dependency_overrides.get(get_current_user_from_headers)

        app.dependency_overrides[get_db] = _pg_get_db
        app.dependency_overrides[get_current_user_from_headers] = _fake_user
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        async def _teardown():
            async with _pg_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await _pg_engine.dispose()

        asyncio.run(_teardown())

        # Restore whatever the SQLite test modules set at module-level import.
        if cls._prev_db is not None:
            app.dependency_overrides[get_db] = cls._prev_db
        else:
            app.dependency_overrides.pop(get_db, None)

        if cls._prev_user is not None:
            app.dependency_overrides[get_current_user_from_headers] = cls._prev_user
        else:
            app.dependency_overrides.pop(get_current_user_from_headers, None)

    # ------------------------------------------------------------------
    # Step 1: create test + submission
    # ------------------------------------------------------------------

    def test_01_create_test_returns_201(self):
        resp = self.client.post(
            "/v1/api/tests/",
            json={"name": "PG Lifecycle Test", "test_type": "QUIZ", "number_of_questions": 11},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "PG Lifecycle Test"
        # UUID or int id persists and round-trips
        assert data["id"] is not None
        TestQuizSessionLifecyclePostgres.test_id = data["id"]

    def test_02_create_submission_returns_201(self):
        resp = self.client.post(
            "/v1/api/submissions/",
            json={"test_id": self.test_id, "user_id": 100},
        )
        assert resp.status_code == 201, resp.text
        TestQuizSessionLifecyclePostgres.submission_id = resp.json()["id"]

    # ------------------------------------------------------------------
    # Step 2: create session
    # ------------------------------------------------------------------

    def test_03_create_session_status_started(self):
        resp = self.client.post(
            "/v1/api/test-sessions/",
            json={
                "test_id": self.test_id,
                "submission_id": self.submission_id,
                "user_id": 100,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "STARTED"
        assert data["id"] is not None
        # UUID stored as string and echoed back
        assert isinstance(data["id"], str)
        TestQuizSessionLifecyclePostgres.session_id = data["id"]

    # ------------------------------------------------------------------
    # Step 3: Part A
    # ------------------------------------------------------------------

    def test_04_get_part_a_questions_strips_answers(self):
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new=_fake_fetch,
        ):
            resp = self.client.get(
                f"/v1/api/test-sessions/{self.session_id}/part-a/questions"
            )
        assert resp.status_code == 200, resp.text
        qs = resp.json()["questions"]
        assert len(qs) > 0
        for q in qs:
            assert "correct_answers" not in q, "answer key leaked to client"
        TestQuizSessionLifecyclePostgres.part_a_questions = qs

    def test_05_submit_part_a_all_correct_scores_100(self):
        answers = [
            {"question_id": q["question_id"], "selected_answers": [1]}
            for q in self.part_a_questions
        ]
        resp = self.client.post(
            f"/v1/api/test-sessions/{self.session_id}/part-a/submit",
            json={"session_id": self.session_id, "answers": answers},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["score"] == 100.0

    # ------------------------------------------------------------------
    # Step 4: Part B
    # ------------------------------------------------------------------

    def test_06_get_part_b_questions_after_part_a(self):
        with patch(
            "src.services.quiz_session_service.fetch_questions_for_part",
            new=_fake_fetch,
        ):
            resp = self.client.get(
                f"/v1/api/test-sessions/{self.session_id}/part-b/questions"
            )
        assert resp.status_code == 200, resp.text
        qs = resp.json()["questions"]
        assert len(qs) > 0
        TestQuizSessionLifecyclePostgres.part_b_questions = qs

    def test_07_submit_part_b_all_correct_scores_100(self):
        answers = [
            {"question_id": q["question_id"], "selected_answers": [1]}
            for q in self.part_b_questions
        ]
        resp = self.client.post(
            f"/v1/api/test-sessions/{self.session_id}/part-b/submit",
            json={"session_id": self.session_id, "answers": answers},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["score"] == 100.0

    # ------------------------------------------------------------------
    # Step 5: verify final state in Postgres
    # ------------------------------------------------------------------

    def test_08_session_status_completed_in_postgres(self):
        resp = self.client.get(f"/v1/api/test-sessions/{self.session_id}/status")
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "COMPLETED"
        assert resp.json()["current_part"] is None

    def test_09_get_session_by_submission_uuid_roundtrip(self):
        """Verify UUID session ID survives Postgres round-trip and equals what was stored."""
        resp = self.client.get(
            f"/v1/api/test-sessions/by-submission/{self.submission_id}"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == self.session_id


class TestCrudPostgres:
    """
    Basic CRUD verifications that SQLite masks:
    - Integer auto-increment IDs
    - FK constraint enforcement (test must exist before submission)
    - JSON columns round-trip through Postgres jsonb
    """

    @classmethod
    def setup_class(cls):
        async def _bootstrap():
            async with _pg_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(_bootstrap())
        cls._prev_db = app.dependency_overrides.get(get_db)
        cls._prev_user = app.dependency_overrides.get(get_current_user_from_headers)
        app.dependency_overrides[get_db] = _pg_get_db
        app.dependency_overrides[get_current_user_from_headers] = _fake_user
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        if cls._prev_db is not None:
            app.dependency_overrides[get_db] = cls._prev_db
        else:
            app.dependency_overrides.pop(get_db, None)
        if cls._prev_user is not None:
            app.dependency_overrides[get_current_user_from_headers] = cls._prev_user
        else:
            app.dependency_overrides.pop(get_current_user_from_headers, None)

    def test_skill_crud_postgres(self):
        resp = self.client.post(
            "/v1/api/skills/",
            json={"name": "PG Skill", "description": "Postgres CRUD test"},
        )
        assert resp.status_code == 201, resp.text
        skill_id = resp.json()["id"]

        resp = self.client.get(f"/v1/api/skills/{skill_id}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "PG Skill"

        resp = self.client.delete(f"/v1/api/skills/{skill_id}/")
        assert resp.status_code == 204

    def test_test_with_skill_ids_postgres(self):
        skill = self.client.post(
            "/v1/api/skills/", json={"name": "PG Linked Skill", "description": "linked"}
        ).json()
        resp = self.client.post(
            "/v1/api/tests/",
            json={"name": "PG Test With Skill", "test_type": "QUIZ", "skill_ids": [skill["id"]]},
        )
        assert resp.status_code == 201, resp.text
        assert any(s["id"] == skill["id"] for s in resp.json()["skills"])

    def test_submission_fk_enforced_postgres(self):
        """Submission referencing non-existent test must return 4xx, not crash."""
        resp = self.client.post(
            "/v1/api/submissions/",
            json={"test_id": 999999, "user_id": 1},
        )
        assert resp.status_code in (400, 404, 422), (
            f"Expected 4xx for FK violation, got {resp.status_code}"
        )
