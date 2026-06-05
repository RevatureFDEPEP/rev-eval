import os

# Must be set BEFORE importing main or any src.* — pydantic Settings and the
# async engine both read these at module load time.
# DATABASE_URL overrides the postgres URL so SQLite is used instead.
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
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
# engine is already pointing at SQLite because DATABASE_URL was set above
from src.db.session import get_db, engine, Base
# Import all models so Base.metadata knows about every table before create_all
from src.models.test import Test
from src.models.skill import Skill
from src.models.test_skill import TestSkill
from src.models.test_submission import TestSubmission
from src.utils.dependencies import get_current_user_from_headers

# Bind test sessions to the same SQLite engine
TestingAsyncSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables():
    # Run create_all through the async engine so SQLite tables exist before tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Module-level call — runs once before any test, no event loop yet at this point
asyncio.run(_create_tables())


async def override_get_db():
    # Yield a fresh async SQLite session instead of the real PostgreSQL one
    async with TestingAsyncSession() as db:
        yield db


# Fake trainer returned instead of calling user-service over HTTP
FAKE_TRAINER = {"id": 1, "email": "trainer@test.com", "role": "TRAINER", "full_name": "Test Trainer"}


async def override_get_current_user():
    # Skip X-User-* header resolution and user-service HTTP call
    return FAKE_TRAINER


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_from_headers] = override_get_current_user

client = TestClient(app)


class TestHealth:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSkills:
    # Skills routes have no auth dependency — no headers needed

    def test_create_skill(self):
        response = client.post("/v1/api/skills/", json={
            "name": "Python",
            "description": "Python programming language"
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Python"

    def test_list_skills(self):
        response = client.get("/v1/api/skills/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_skill_by_id(self):
        # Create a skill then fetch it by the returned id
        create_resp = client.post("/v1/api/skills/", json={"name": "SQL", "description": "Databases"})
        skill_id = create_resp.json()["id"]
        response = client.get(f"/v1/api/skills/{skill_id}/")
        assert response.status_code == 200
        assert response.json()["name"] == "SQL"

    def test_get_skill_not_found(self):
        # Non-existent id must return 404, not 500
        response = client.get("/v1/api/skills/99999/")
        assert response.status_code == 404

    def test_update_skill(self):
        create_resp = client.post("/v1/api/skills/", json={"name": "Java", "description": "OOP"})
        skill_id = create_resp.json()["id"]
        response = client.put(f"/v1/api/skills/{skill_id}/", json={
            "name": "Java",
            "description": "Enterprise Java"
        })
        assert response.status_code == 200
        assert response.json()["description"] == "Enterprise Java"

    def test_delete_skill(self):
        create_resp = client.post("/v1/api/skills/", json={"name": "TempSkill", "description": "will be deleted"})
        skill_id = create_resp.json()["id"]
        del_resp = client.delete(f"/v1/api/skills/{skill_id}/")
        assert del_resp.status_code == 204
        # Verify it is truly gone
        get_resp = client.get(f"/v1/api/skills/{skill_id}/")
        assert get_resp.status_code == 404

    def test_delete_skill_not_found(self):
        response = client.delete("/v1/api/skills/99999/")
        assert response.status_code == 404


class TestTests:
    # Create/Update/Delete use get_current_user_id which reads from get_current_user_from_headers
    # The override returns FAKE_TRAINER (id=1), so all created tests have created_by_id=1

    def test_create_test(self):
        response = client.post("/v1/api/tests/", json={
            "name": "Python Basics Quiz",
            "test_type": "QUIZ",
            "number_of_questions": 10
        })
        assert response.status_code == 201
        assert response.json()["name"] == "Python Basics Quiz"
        # created_by_id is set from the auth override — FAKE_TRAINER id=1
        assert response.json()["created_by_id"] == 1

    def test_create_test_with_skill(self):
        # Create a skill first, then link it via skill_ids in the test payload
        skill_resp = client.post("/v1/api/skills/", json={"name": "FastAPI", "description": "Web framework"})
        skill_id = skill_resp.json()["id"]
        response = client.post("/v1/api/tests/", json={
            "name": "FastAPI Interview",
            "test_type": "INTERVIEW",
            "skill_ids": [skill_id]
        })
        assert response.status_code == 201
        # TestOut.skills is eager-loaded from the test_skills join table
        assert any(s["id"] == skill_id for s in response.json()["skills"])

    def test_list_tests(self):
        response = client.get("/v1/api/tests/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_test_by_id(self):
        create_resp = client.post("/v1/api/tests/", json={"name": "Fetch Me", "test_type": "QUIZ"})
        test_id = create_resp.json()["id"]
        response = client.get(f"/v1/api/tests/{test_id}/")
        assert response.status_code == 200
        assert response.json()["id"] == test_id

    def test_get_test_not_found(self):
        response = client.get("/v1/api/tests/99999/")
        assert response.status_code == 404

    def test_update_test(self):
        # Creator (id=1) is allowed to update — ownership check in test_route.py passes
        create_resp = client.post("/v1/api/tests/", json={"name": "Old Name", "test_type": "QUIZ"})
        test_id = create_resp.json()["id"]
        response = client.put(f"/v1/api/tests/{test_id}/", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_delete_test(self):
        create_resp = client.post("/v1/api/tests/", json={"name": "Delete Me", "test_type": "QUIZ"})
        test_id = create_resp.json()["id"]
        del_resp = client.delete(f"/v1/api/tests/{test_id}/")
        assert del_resp.status_code == 204
        # Test should no longer exist
        get_resp = client.get(f"/v1/api/tests/{test_id}/")
        assert get_resp.status_code == 404

    def test_list_tests_created_by_user(self):
        response = client.get("/v1/api/tests/created-by/1/")
        assert response.status_code == 200
        # All returned tests must belong to user 1 (our fake trainer)
        assert all(t["created_by_id"] == 1 for t in response.json())


class TestSubmissions:
    def _create_test(self) -> int:
        # Helper — create a test so submissions have a valid test_id to reference
        resp = client.post("/v1/api/tests/", json={"name": "Submission Test", "test_type": "QUIZ"})
        return resp.json()["id"]

    def test_create_submission(self):
        test_id = self._create_test()
        response = client.post("/v1/api/submissions/", json={
            "test_id": test_id,
            "user_id": 42,      # participant's user-service id
            "status": "ASSIGNED"
        })
        assert response.status_code == 201
        assert response.json()["user_id"] == 42
        assert response.json()["status"] == "ASSIGNED"
        # test relationship is eager-loaded and shows test metadata
        assert response.json()["test"]["id"] == test_id

    def test_list_all_submissions(self):
        # No user_id param + trainer role → list_all_submissions branch in route
        response = client.get("/v1/api/submissions/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_submissions_by_user(self):
        # user_id query param filters to only that participant's submissions
        test_id = self._create_test()
        client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": 99})
        response = client.get("/v1/api/submissions/?user_id=99")
        assert response.status_code == 200
        assert all(s["user_id"] == 99 for s in response.json())

    def test_get_submission_by_id(self):
        test_id = self._create_test()
        create_resp = client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": 10})
        submission_id = create_resp.json()["id"]
        response = client.get(f"/v1/api/submissions/{submission_id}/")
        assert response.status_code == 200
        assert response.json()["id"] == submission_id

    def test_get_submission_not_found(self):
        response = client.get("/v1/api/submissions/99999/")
        assert response.status_code == 404

    def test_update_submission_status(self):
        test_id = self._create_test()
        create_resp = client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": 20})
        submission_id = create_resp.json()["id"]
        # Advance through the lifecycle: ASSIGNED → IN_PROGRESS
        response = client.put(f"/v1/api/submissions/{submission_id}/", json={"status": "IN_PROGRESS"})
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"

    def test_update_submission_score(self):
        test_id = self._create_test()
        create_resp = client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": 21})
        submission_id = create_resp.json()["id"]
        # Record AI evaluation results
        response = client.put(f"/v1/api/submissions/{submission_id}/", json={
            "status": "EVALUATED",
            "ai_score": 85,
            "final_score": 85
        })
        assert response.status_code == 200
        assert response.json()["ai_score"] == 85
        assert response.json()["status"] == "EVALUATED"

    def test_delete_submission(self):
        test_id = self._create_test()
        create_resp = client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": 30})
        submission_id = create_resp.json()["id"]
        del_resp = client.delete(f"/v1/api/submissions/{submission_id}/")
        assert del_resp.status_code == 204
        # Confirm deleted
        get_resp = client.get(f"/v1/api/submissions/{submission_id}/")
        assert get_resp.status_code == 404
