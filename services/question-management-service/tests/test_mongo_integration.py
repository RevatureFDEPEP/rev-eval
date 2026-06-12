"""
tests/test_mongo_integration.py

Integration tests for question-management-service against a real MongoDB instance.
Skipped locally; requires the CI MongoDB service container (CI=true).

Covers:
- CRUD round-trip with real ObjectId persistence
- Filter endpoints (by-type, by-skill, by-difficulty, by-tags, combined filter)
- Image-route 404 paths (no MinIO needed)
- 404 for missing document
"""

import os
import asyncio
import pytest

# Set env vars BEFORE any src.* import so pydantic-settings doesn't blow up.
os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("PORT", "8003")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_questions")

_IN_CI = os.environ.get("CI") == "true"

pytestmark = pytest.mark.skipif(
    not _IN_CI,
    reason="MongoDB integration tests require CI service container (CI=true)",
)

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

_MONGO_URL = "mongodb://localhost:27017"
_TEST_DB = "test_questions"


async def _drop_test_db():
    from pymongo import AsyncMongoClient
    mc = AsyncMongoClient(_MONGO_URL)
    await mc.drop_database(_TEST_DB)
    mc.close()


_MCQ_PAYLOAD = {
    "type": "mcq",
    "question_text": "What is the output of print(2 + 2) in Python?",
    "options": [
        {"text": "3"},
        {"text": "4"},
        {"text": "5"},
        {"text": "22"},
    ],
    "correct_answers": [2],
    "difficulty": "easy",
    "skills": ["Python"],
    "tags": ["python", "basics"],
}


class TestQuestionCrudMongo:
    """Full CRUD + filter round-trip against real MongoDB."""

    @classmethod
    def setup_class(cls):
        # TestClient as context manager triggers @app.on_event("startup")
        # which calls init_db() → beanie initialized with MONGO_URI + MONGO_DB.
        cls._tc = TestClient(app)
        cls.client = cls._tc.__enter__()

    @classmethod
    def teardown_class(cls):
        cls._tc.__exit__(None, None, None)
        asyncio.run(_drop_test_db())

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_01_create_mcq_returns_201(self):
        resp = self.client.post("/v1/api/questions/", json=_MCQ_PAYLOAD)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "id" in data
        TestQuestionCrudMongo.mcq_id = data["id"]

    def test_02_create_multi_returns_201(self):
        resp = self.client.post(
            "/v1/api/questions/",
            json={
                "type": "multi",
                "question_text": "Which of the following are Python data structures?",
                "options": [
                    {"text": "List"},
                    {"text": "Tuple"},
                    {"text": "Integer"},
                    {"text": "Dictionary"},
                ],
                "correct_answers": [1, 2, 4],
                "difficulty": "medium",
                "skills": ["Python"],
                "tags": ["python", "data-structures"],
            },
        )
        assert resp.status_code == 201, resp.text
        TestQuestionCrudMongo.multi_id = resp.json()["id"]

    def test_03_get_question_by_id_returns_200(self):
        resp = self.client.get(f"/v1/api/questions/{self.mcq_id}")
        assert resp.status_code == 200, resp.text
        # QuestionResponse serializes with alias _id
        assert resp.json()["_id"] == self.mcq_id

    def test_04_get_all_questions_includes_created(self):
        resp = self.client.get("/v1/api/questions/")
        assert resp.status_code == 200
        ids = [q["_id"] for q in resp.json()]
        assert self.mcq_id in ids

    def test_05_update_question_changes_difficulty(self):
        resp = self.client.put(
            f"/v1/api/questions/{self.mcq_id}",
            json={"difficulty": "hard"},
        )
        assert resp.status_code == 200, resp.text
        updated = self.client.get(f"/v1/api/questions/{self.mcq_id}").json()
        assert updated["difficulty"] == "hard"

    def test_06_get_missing_question_returns_404(self):
        resp = self.client.get("/v1/api/questions/000000000000000000000000")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Filter endpoints
    # ------------------------------------------------------------------

    def test_07_filter_by_skill_returns_question(self):
        resp = self.client.get("/v1/api/questions/by-skill/Python")
        assert resp.status_code == 200
        assert any(q["_id"] == self.mcq_id for q in resp.json())

    def test_08_filter_by_type_mcq(self):
        resp = self.client.get("/v1/api/questions/by-type/mcq")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert all(q["type"] == "mcq" for q in resp.json())

    def test_09_filter_by_difficulty_hard(self):
        resp = self.client.get("/v1/api/questions/by-difficulty/hard")
        assert resp.status_code == 200
        assert any(q["_id"] == self.mcq_id for q in resp.json())

    def test_10_filter_by_tags_returns_question(self):
        resp = self.client.get("/v1/api/questions/by-tags?tags=python")
        assert resp.status_code == 200
        assert any(q["_id"] == self.mcq_id for q in resp.json())

    def test_11_filter_combined_type_and_difficulty(self):
        resp = self.client.get("/v1/api/questions/filter?type=multi&difficulty=medium")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert all(q["type"] == "multi" for q in results)

    def test_12_filter_combined_skill_and_type(self):
        resp = self.client.get("/v1/api/questions/filter?skill=Python&type=mcq")
        assert resp.status_code == 200
        assert any(q["_id"] == self.mcq_id for q in resp.json())

    # ------------------------------------------------------------------
    # Image routes — 404 path (no MinIO needed)
    # ------------------------------------------------------------------

    def test_13_image_download_url_404_for_missing_question(self):
        resp = self.client.get(
            "/v1/api/questions/000000000000000000000000/image/download-url"
        )
        assert resp.status_code == 404

    def test_14_image_upload_url_404_for_missing_question(self):
        resp = self.client.post(
            "/v1/api/questions/000000000000000000000000/image/upload-url"
        )
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_15_delete_question_returns_200(self):
        resp = self.client.delete(f"/v1/api/questions/{self.mcq_id}")
        assert resp.status_code == 200
        gone = self.client.get(f"/v1/api/questions/{self.mcq_id}")
        assert gone.status_code == 404
