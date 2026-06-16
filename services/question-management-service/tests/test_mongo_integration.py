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

    def test_10b_filter_by_tags_whitespace_tag_returns_400(self):
        # tag of only whitespace → service strips → empty list → HTTPException 400
        resp = self.client.get("/v1/api/questions/by-tags?tags=%20%20%20")
        assert resp.status_code == 400

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

    def test_14b_image_download_url_200_for_valid_question(self):
        # generate_presigned_get_url uses local signing — no MinIO required.
        resp = self.client.get(f"/v1/api/questions/{self.mcq_id}/image/download-url")
        assert resp.status_code == 200
        body = resp.json()
        assert "url" in body
        assert body["key"] == f"questions/{self.mcq_id}/image"

    def test_14c_image_upload_url_502_without_minio(self):
        # ensure_bucket() tries to reach MinIO; 502 expected in CI without it.
        resp = self.client.post(f"/v1/api/questions/{self.mcq_id}/image/upload-url")
        assert resp.status_code in (200, 502)

    # ------------------------------------------------------------------
    # TRUE_FALSE and TEXT question types
    # ------------------------------------------------------------------

    def test_15a_create_true_false_returns_201(self):
        resp = self.client.post(
            "/v1/api/questions/",
            json={
                "type": "true_false",
                "question_text": "Is Python an interpreted programming language?",
                "correct_answers": [True],
                "difficulty": "easy",
                "skills": ["Python"],
                "tags": ["python", "basics"],
            },
        )
        assert resp.status_code == 201, resp.text
        TestQuestionCrudMongo.tf_id = resp.json()["id"]

    def test_15b_update_true_false_valid_correct_answers(self):
        resp = self.client.put(
            f"/v1/api/questions/{self.tf_id}",
            json={"correct_answers": [False]},
        )
        assert resp.status_code == 200, resp.text

    def test_15c_update_true_false_with_options_returns_400(self):
        resp = self.client.put(
            f"/v1/api/questions/{self.tf_id}",
            json={"options": [{"text": "Option A"}, {"text": "Option B"}]},
        )
        assert resp.status_code == 400

    def test_15d_create_text_returns_201(self):
        resp = self.client.post(
            "/v1/api/questions/",
            json={
                "type": "text",
                "question_text": "Explain what object-oriented programming means.",
                "sample_answer": "OOP is a paradigm based on objects that contain data and methods.",
                "difficulty": "medium",
                "skills": ["Programming"],
                "tags": ["programming", "concepts"],
            },
        )
        assert resp.status_code == 201, resp.text
        TestQuestionCrudMongo.text_id = resp.json()["id"]

    def test_15e_update_text_with_options_returns_400(self):
        resp = self.client.put(
            f"/v1/api/questions/{self.text_id}",
            json={"options": [{"text": "Option A"}, {"text": "Option B"}]},
        )
        assert resp.status_code == 400

    def test_15f_update_text_with_correct_answers_returns_400(self):
        resp = self.client.put(
            f"/v1/api/questions/{self.text_id}",
            json={"correct_answers": [1]},
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # Service validation errors (400 paths)
    # ------------------------------------------------------------------

    def test_15g_filter_invalid_type_returns_400(self):
        resp = self.client.get("/v1/api/questions/by-type/invalid_type")
        assert resp.status_code == 400

    def test_15h_filter_invalid_difficulty_returns_400(self):
        resp = self.client.get("/v1/api/questions/by-difficulty/extreme")
        assert resp.status_code == 400

    def test_15i_filter_no_params_returns_400(self):
        resp = self.client.get("/v1/api/questions/filter")
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_15_delete_question_returns_200(self):
        resp = self.client.delete(f"/v1/api/questions/{self.mcq_id}")
        assert resp.status_code == 200
        gone = self.client.get(f"/v1/api/questions/{self.mcq_id}")
        assert gone.status_code == 404
