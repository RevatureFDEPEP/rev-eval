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
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
# engine is already pointing at SQLite because DATABASE_URL was set above
from src.db.session import get_db, engine, Base
# Import all models so Base.metadata knows about every table before create_all
from src.models.test import Test  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401
from src.models.quiz_session import QuizSession  # noqa: F401
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


# ---------------------------------------------------------------------------
# Helpers for mocking httpx.AsyncClient
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, status_code: int, data: dict = None):
        self.status_code = status_code
        self._data = data or {}
        self.text = ""

    def json(self):
        return self._data


def _mock_client(get_data=None, get_status=200, post_data=None, post_status=201, patch_status=200):
    """Return a class that can replace httpx.AsyncClient in any context manager usage."""
    _get = _FakeResp(get_status, get_data or {})
    _post = _FakeResp(post_status, post_data or {})
    _patch = _FakeResp(patch_status, {})

    class _Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, *a, **k):
            return _get

        async def post(self, *a, **k):
            return _post

        async def patch(self, *a, **k):
            return _patch

    return _Client


# ---------------------------------------------------------------------------
# Extended tests — test_service.py branches
# ---------------------------------------------------------------------------

class TestTestsExtended:
    """Cover skill-loop and skills-update branches in test_service.py."""

    def test_get_test_by_id_with_skills_covers_loop(self):
        skill = client.post("/v1/api/skills/", json={"name": "LoopSkill", "description": "loop"}).json()
        test = client.post("/v1/api/tests/", json={
            "name": "LoopTest", "test_type": "QUIZ", "skill_ids": [skill["id"]]
        }).json()
        resp = client.get(f"/v1/api/tests/{test['id']}/")
        assert resp.status_code == 200
        assert any(s["id"] == skill["id"] for s in resp.json()["skills"])

    def test_update_test_with_skill_ids(self):
        s1 = client.post("/v1/api/skills/", json={"name": "OldSkillU", "description": "o"}).json()
        s2 = client.post("/v1/api/skills/", json={"name": "NewSkillU", "description": "n"}).json()
        test = client.post("/v1/api/tests/", json={
            "name": "SkillSwap", "test_type": "QUIZ", "skill_ids": [s1["id"]]
        }).json()
        resp = client.put(f"/v1/api/tests/{test['id']}/", json={
            "name": "SkillSwap Updated", "skill_ids": [s2["id"]]
        })
        assert resp.status_code == 200
        assert any(s["id"] == s2["id"] for s in resp.json()["skills"])

    def test_list_tests_with_submissions_by_user(self):
        test = client.post("/v1/api/tests/", json={"name": "ParticipantTest", "test_type": "QUIZ"}).json()
        client.post("/v1/api/submissions/", json={"test_id": test["id"], "user_id": 77})
        resp = client.get("/v1/api/tests/submissions-by/77/")
        assert resp.status_code == 200
        assert any(t["id"] == test["id"] for t in resp.json())


# ---------------------------------------------------------------------------
# Extended tests — test_submission_service.py + route branches
# ---------------------------------------------------------------------------

class TestSubmissionsExtended:
    """Cover not-found branches, trainer endpoints, bulk-assign, and trainer review."""

    def _create_test(self) -> int:
        return client.post("/v1/api/tests/", json={"name": "ExtTest", "test_type": "QUIZ"}).json()["id"]

    def test_update_submission_not_found(self):
        resp = client.put("/v1/api/submissions/99999/", json={"status": "IN_PROGRESS"})
        assert resp.status_code == 404

    def test_delete_submission_not_found(self):
        resp = client.delete("/v1/api/submissions/99999/")
        assert resp.status_code == 404

    def test_graded_submissions_endpoint(self):
        resp = client.get("/v1/api/submissions/graded")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_review_details_not_found(self):
        resp = client.get("/v1/api/submissions/99999/review-details")
        assert resp.status_code == 404

    def test_review_details_existing(self):
        tid = self._create_test()
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 70}).json()
        resp = client.get(f"/v1/api/submissions/{sub['id']}/review-details")
        assert resp.status_code == 200
        assert "submission" in resp.json()

    def test_submit_trainer_review(self):
        tid = self._create_test()
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 80}).json()
        client.put(f"/v1/api/submissions/{sub['id']}/", json={"status": "EVALUATED"})
        resp = client.post(f"/v1/api/submissions/{sub['id']}/trainer-review", json={
            "trainer_score": 88,
            "feedback": "Well done"
        })
        assert resp.status_code == 200
        assert resp.json()["trainer_score"] == 88
        assert resp.json()["status"] == "GRADED"

    def test_submit_trainer_review_wrong_status(self):
        tid = self._create_test()
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 81}).json()
        resp = client.post(f"/v1/api/submissions/{sub['id']}/trainer-review", json={
            "trainer_score": 75
        })
        assert resp.status_code == 404

    def test_trainer_evaluated_endpoint(self):
        Mock = _mock_client(get_data={"id": 9, "first_name": "Alice", "last_name": "S", "email": "a@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/evaluated")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trainer_all_endpoint(self):
        Mock = _mock_client(get_data={"id": 9, "first_name": "Bob", "last_name": "J", "email": "b@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/all")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_bulk_assign_existing_user(self):
        tid = self._create_test()
        Mock = _mock_client(get_data={"id": 50, "email": "bulk@test.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["bulk@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["success_count"] == 1

    def test_bulk_assign_new_user_invite(self):
        tid = self._create_test()
        Mock = _mock_client(
            get_status=404,
            post_data={"id": 51, "email": "new@test.com"},
            post_status=201
        )
        with patch("httpx.AsyncClient", Mock):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["new@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["success_count"] == 1

    def test_bulk_assign_invite_failure(self):
        tid = self._create_test()
        Mock = _mock_client(get_status=404, post_status=500)
        with patch("httpx.AsyncClient", Mock):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["fail@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["failure_count"] == 1

    def test_bulk_assign_user_service_unexpected_status(self):
        tid = self._create_test()
        Mock = _mock_client(get_status=503)
        with patch("httpx.AsyncClient", Mock):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["err@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["failure_count"] == 1


# ---------------------------------------------------------------------------
# Unit tests for src/utils/dependencies.py
# ---------------------------------------------------------------------------

class TestDependencies:
    """Call dependency functions directly to cover auth/role logic."""

    def test_missing_headers_raises_401(self):
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_user_from_headers

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_user_from_headers(None, None, None))
        assert exc.value.status_code == 401

    def test_resolve_by_user_id(self):
        from src.utils.dependencies import get_current_user_from_headers

        Mock = _mock_client(get_data={"id": 1, "role": "TRAINER"})

        async def call():
            with patch("httpx.AsyncClient", Mock):
                return await get_current_user_from_headers("1", None, None)

        result = asyncio.run(call())
        assert result["role"] == "TRAINER"

    def test_resolve_by_email(self):
        from src.utils.dependencies import get_current_user_from_headers

        Mock = _mock_client(get_data={"id": 2, "role": "PARTICIPANT"})

        async def call():
            with patch("httpx.AsyncClient", Mock):
                return await get_current_user_from_headers(None, "x@test.com", None)

        result = asyncio.run(call())
        assert result["id"] == 2

    def test_user_not_found_raises_401(self):
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_user_from_headers

        Mock = _mock_client(get_status=404)

        async def call():
            with patch("httpx.AsyncClient", Mock):
                return await get_current_user_from_headers("9", None, None)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(call())
        assert exc.value.status_code == 401

    def test_service_5xx_raises_503(self):
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_user_from_headers

        Mock = _mock_client(get_status=500)

        async def call():
            with patch("httpx.AsyncClient", Mock):
                return await get_current_user_from_headers("1", None, None)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(call())
        assert exc.value.status_code == 503

    def test_request_error_raises_503(self):
        import httpx as _httpx
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_user_from_headers

        class ErrClient:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def get(self, *a, **k):
                raise _httpx.RequestError("refused")

        async def call():
            with patch("httpx.AsyncClient", ErrClient):
                return await get_current_user_from_headers("1", None, None)

        with pytest.raises(HTTPException) as exc:
            asyncio.run(call())
        assert exc.value.status_code == 503

    def test_get_current_trainer_ok(self):
        from src.utils.dependencies import get_current_trainer

        result = asyncio.run(get_current_trainer({"id": 1, "role": "TRAINER"}))
        assert result["role"] == "TRAINER"

    def test_get_current_trainer_forbidden(self):
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_trainer

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_trainer({"id": 1, "role": "PARTICIPANT"}))
        assert exc.value.status_code == 403

    def test_get_current_participant_ok(self):
        from src.utils.dependencies import get_current_participant

        result = asyncio.run(get_current_participant({"id": 2, "role": "PARTICIPANT"}))
        assert result["role"] == "PARTICIPANT"

    def test_get_current_participant_forbidden(self):
        from fastapi import HTTPException
        from src.utils.dependencies import get_current_participant

        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_participant({"id": 1, "role": "TRAINER"}))
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Route edge cases — auth / ownership branches
# ---------------------------------------------------------------------------

class TestRouteEdgeCases:
    """Cover auth and ownership branches in test_route.py and test_submission_route.py."""

    def _set_user(self, user_dict):
        async def _u():
            return user_dict
        app.dependency_overrides[get_current_user_from_headers] = _u

    def _restore_user(self):
        app.dependency_overrides[get_current_user_from_headers] = override_get_current_user

    # test_route.py line 21: get_current_user_id raises 401 when user has no id
    def test_create_test_user_without_id(self):
        self._set_user({"role": "TRAINER"})
        try:
            resp = client.post("/v1/api/tests/", json={"name": "X", "test_type": "QUIZ"})
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_route.py lines 59-63: update 403 when caller is not the creator
    def test_update_test_forbidden(self):
        test = client.post("/v1/api/tests/", json={"name": "OwnerTest", "test_type": "QUIZ"}).json()
        self._set_user({"id": 2, "role": "TRAINER"})
        try:
            resp = client.put(f"/v1/api/tests/{test['id']}/", json={"name": "Hijacked"})
            assert resp.status_code == 403
        finally:
            self._restore_user()

    # test_route.py lines 85-89: delete 403 when caller is not the creator
    def test_delete_test_forbidden(self):
        test = client.post("/v1/api/tests/", json={"name": "OwnerTest2", "test_type": "QUIZ"}).json()
        self._set_user({"id": 2, "role": "TRAINER"})
        try:
            resp = client.delete(f"/v1/api/tests/{test['id']}/")
            assert resp.status_code == 403
        finally:
            self._restore_user()

    # test_submission_route.py line 47: PARTICIPANT sees only own submissions
    def test_list_submissions_as_participant(self):
        self._set_user({"id": 5, "role": "PARTICIPANT"})
        try:
            resp = client.get("/v1/api/submissions/")
            assert resp.status_code == 200
            assert all(s["user_id"] == 5 for s in resp.json())
        finally:
            self._restore_user()

    # test_submission_route.py line 101: /trainer/evaluated 401 when no current_user
    def test_evaluated_no_current_user(self):
        self._set_user(None)
        try:
            resp = client.get("/v1/api/submissions/trainer/evaluated")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 105: /trainer/evaluated 401 when user has no id
    def test_evaluated_no_trainer_id(self):
        self._set_user({"role": "TRAINER"})
        try:
            resp = client.get("/v1/api/submissions/trainer/evaluated")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 125: /trainer/all 401 when no current_user
    def test_all_subs_no_current_user(self):
        self._set_user(None)
        try:
            resp = client.get("/v1/api/submissions/trainer/all")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 129: /trainer/all 401 when user has no id
    def test_all_subs_no_trainer_id(self):
        self._set_user({"role": "TRAINER"})
        try:
            resp = client.get("/v1/api/submissions/trainer/all")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 144: /graded 401 when no current_user
    def test_graded_no_current_user(self):
        self._set_user(None)
        try:
            resp = client.get("/v1/api/submissions/graded")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 165: /review-details 401 when no current_user
    def test_review_details_no_current_user(self):
        self._set_user(None)
        try:
            resp = client.get("/v1/api/submissions/1/review-details")
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py lines 171-172: /review-details 500 on unexpected exception
    def test_review_details_unexpected_exception(self):
        from unittest.mock import AsyncMock
        from src.services.test_submission_service import TestSubmissionService
        with patch.object(TestSubmissionService, "get_submission_review_details",
                          new=AsyncMock(side_effect=RuntimeError("boom"))):
            resp = client.get("/v1/api/submissions/1/review-details")
        assert resp.status_code == 500

    # test_submission_route.py line 194: /trainer-review 401 when no current_user
    def test_trainer_review_no_current_user(self):
        self._set_user(None)
        try:
            resp = client.post("/v1/api/submissions/1/trainer-review", json={"trainer_score": 75})
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py line 198: /trainer-review 401 when user has no id
    def test_trainer_review_no_trainer_id(self):
        self._set_user({"role": "TRAINER"})
        try:
            resp = client.post("/v1/api/submissions/1/trainer-review", json={"trainer_score": 75})
            assert resp.status_code == 401
        finally:
            self._restore_user()

    # test_submission_route.py lines 206-207: /trainer-review 500 on unexpected exception
    def test_trainer_review_unexpected_exception(self):
        from unittest.mock import AsyncMock
        from src.services.test_submission_service import TestSubmissionService
        with patch.object(TestSubmissionService, "submit_trainer_review",
                          new=AsyncMock(side_effect=RuntimeError("boom"))):
            resp = client.post("/v1/api/submissions/1/trainer-review", json={"trainer_score": 75})
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Service-level coverage gaps
# ---------------------------------------------------------------------------

class TestServiceCoverageGaps:
    """Cover uncovered branches in services and db/session."""

    def _create_test(self, test_type: str = "QUIZ") -> int:
        return client.post("/v1/api/tests/", json={"name": "GapTest", "test_type": test_type}).json()["id"]

    def _create_evaluated_sub(self, tid: int, uid: int) -> int:
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": uid}).json()
        client.put(f"/v1/api/submissions/{sub['id']}/", json={"status": "EVALUATED"})
        return sub["id"]

    # db/session.py lines 48-62: init_db success path
    def test_init_db_success(self):
        from src.db.session import init_db
        asyncio.run(init_db())

    # test_submission_service.py line 198: bulk_assign raises when test not found
    def test_bulk_assign_test_not_found(self):
        from src.services.test_submission_service import TestSubmissionService
        from src.schemas.test_submission_schema import BulkAssignRequest

        async def run():
            async with TestingAsyncSession() as db:
                req = BulkAssignRequest(test_id=99999, participant_emails=["x@test.com"])
                await TestSubmissionService.bulk_assign_test(db, req, {"id": 1})

        with pytest.raises(ValueError, match="not found"):
            asyncio.run(run())

    # test_submission_service.py line 196: bulk_assign raises ValueError when test_id not found
    def test_bulk_assign_test_not_found_http(self):
        resp = client.post("/v1/api/submissions/bulk-assign", json={
            "test_id": 99999,
            "participant_emails": ["ghost@test.com"]
        })
        assert resp.status_code == 404

    # test_submission_service.py lines 253-258: httpx.RequestError inside bulk_assign
    def test_bulk_assign_request_error(self):
        import httpx as _httpx

        class ErrClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **k): raise _httpx.RequestError("refused")
            async def post(self, *a, **k): raise _httpx.RequestError("refused")

        tid = self._create_test()
        with patch("httpx.AsyncClient", ErrClient):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["neterr@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["failure_count"] == 1

    # test_submission_service.py lines 259-264: generic Exception inside bulk_assign
    def test_bulk_assign_generic_exception(self):
        class ExcClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **k): raise RuntimeError("unexpected")
            async def post(self, *a, **k): raise RuntimeError("unexpected")

        tid = self._create_test()
        with patch("httpx.AsyncClient", ExcClient):
            resp = client.post("/v1/api/submissions/bulk-assign", json={
                "test_id": tid,
                "participant_emails": ["exc@test.com"]
            })
        assert resp.status_code == 201
        assert resp.json()["failure_count"] == 1

    # test_submission_service.py lines 324-325: first_name only in evaluated list
    def test_trainer_evaluated_first_name_only(self):
        tid = self._create_test()
        self._create_evaluated_sub(tid, 200)
        Mock = _mock_client(get_data={"id": 200, "first_name": "Alice", "last_name": "", "email": "a@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/evaluated")
        assert resp.status_code == 200

    # test_submission_service.py lines 326-327: last_name only in evaluated list
    def test_trainer_evaluated_last_name_only(self):
        tid = self._create_test()
        self._create_evaluated_sub(tid, 201)
        Mock = _mock_client(get_data={"id": 201, "first_name": "", "last_name": "Smith", "email": "s@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/evaluated")
        assert resp.status_code == 200

    # test_submission_service.py line 329: email fallback in evaluated list
    def test_trainer_evaluated_email_fallback(self):
        tid = self._create_test()
        self._create_evaluated_sub(tid, 202)
        Mock = _mock_client(get_data={"id": 202, "first_name": "", "last_name": "", "email": "nb@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/evaluated")
        assert resp.status_code == 200

    # test_submission_service.py lines 332-334: user fetch exception in evaluated list
    def test_trainer_evaluated_user_fetch_exception(self):
        import httpx as _httpx

        class ErrClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **k): raise _httpx.RequestError("refused")

        tid = self._create_test()
        self._create_evaluated_sub(tid, 203)
        with patch("httpx.AsyncClient", ErrClient):
            resp = client.get("/v1/api/submissions/trainer/evaluated")
        assert resp.status_code == 200

    # test_submission_service.py lines 419-420: first_name only in all-for-trainer list
    def test_trainer_all_first_name_only(self):
        tid = self._create_test()
        client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 210})
        Mock = _mock_client(get_data={"id": 210, "first_name": "Bob", "last_name": "", "email": "b@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/all")
        assert resp.status_code == 200

    # test_submission_service.py lines 421-422: last_name only in all-for-trainer list
    def test_trainer_all_last_name_only(self):
        tid = self._create_test()
        client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 211})
        Mock = _mock_client(get_data={"id": 211, "first_name": "", "last_name": "Jones", "email": "j@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/all")
        assert resp.status_code == 200

    # test_submission_service.py line 425: email fallback in all-for-trainer list
    def test_trainer_all_email_fallback(self):
        tid = self._create_test()
        client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 212})
        Mock = _mock_client(get_data={"id": 212, "first_name": "", "last_name": "", "email": "fl@t.com"})
        with patch("httpx.AsyncClient", Mock):
            resp = client.get("/v1/api/submissions/trainer/all")
        assert resp.status_code == 200

    # test_submission_service.py lines 429-431: user fetch exception in all-for-trainer list
    def test_trainer_all_user_fetch_exception(self):
        import httpx as _httpx

        class ErrClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **k): raise _httpx.RequestError("refused")

        tid = self._create_test()
        client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 213})
        with patch("httpx.AsyncClient", ErrClient):
            resp = client.get("/v1/api/submissions/trainer/all")
        assert resp.status_code == 200

    # test_submission_service.py lines 512-514: submit_trainer_review submission not found
    def test_submit_trainer_review_submission_not_found(self):
        resp = client.post("/v1/api/submissions/99999/trainer-review", json={"trainer_score": 75})
        assert resp.status_code == 404

    # test_submission_service.py lines 542-555: INTERVIEW type with trainer_evaluation → MongoDB patch
    def test_submit_trainer_review_interview_with_evaluation(self):
        tid = self._create_test(test_type="INTERVIEW")
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 91}).json()
        client.put(f"/v1/api/submissions/{sub['id']}/", json={"status": "EVALUATED"})
        Mock = _mock_client(patch_status=200)
        from src.config.settings import settings as svc_settings
        with patch("httpx.AsyncClient", Mock), \
             patch.object(svc_settings, "INTERVIEW_SERVICE_URL", "http://interview-svc"):
            resp = client.post(f"/v1/api/submissions/{sub['id']}/trainer-review", json={
                "trainer_score": 90,
                "trainer_evaluation": {"skill": "good"}
            })
        assert resp.status_code == 200
        assert resp.json()["trainer_score"] == 90

    # test_submission_service.py lines 556-558: MongoDB patch returns non-200 (warning path)
    def test_submit_trainer_review_interview_patch_fails(self):
        tid = self._create_test(test_type="INTERVIEW")
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 92}).json()
        client.put(f"/v1/api/submissions/{sub['id']}/", json={"status": "EVALUATED"})
        Mock = _mock_client(patch_status=500)
        from src.config.settings import settings as svc_settings
        with patch("httpx.AsyncClient", Mock), \
             patch.object(svc_settings, "INTERVIEW_SERVICE_URL", "http://interview-svc"):
            resp = client.post(f"/v1/api/submissions/{sub['id']}/trainer-review", json={
                "trainer_score": 85,
                "trainer_evaluation": {"skill": "ok"}
            })
        assert resp.status_code == 200

    # test_submission_service.py lines 559-561: MongoDB patch raises exception (caught)
    def test_submit_trainer_review_interview_patch_exception(self):
        import httpx as _httpx

        class ExcPatchClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def patch(self, *a, **k): raise _httpx.RequestError("failed")
            async def get(self, *a, **k): return _FakeResp(200, {})

        tid = self._create_test(test_type="INTERVIEW")
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 93}).json()
        client.put(f"/v1/api/submissions/{sub['id']}/", json={"status": "EVALUATED"})
        from src.config.settings import settings as svc_settings
        with patch("httpx.AsyncClient", ExcPatchClient), \
             patch.object(svc_settings, "INTERVIEW_SERVICE_URL", "http://interview-svc"):
            resp = client.post(f"/v1/api/submissions/{sub['id']}/trainer-review", json={
                "trainer_score": 80,
                "trainer_evaluation": {"skill": "pass"}
            })
        assert resp.status_code == 200

    # test_submission_service.py lines 471-472: transcript fetch returns 200
    def test_review_details_transcript_success(self):
        tid = self._create_test()
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 300}).json()
        Mock = _mock_client(get_data={"turns": []})
        from src.config.settings import settings as svc_settings
        with patch("httpx.AsyncClient", Mock), \
             patch.object(svc_settings, "INTERVIEW_SERVICE_URL", "http://interview-svc"):
            resp = client.get(f"/v1/api/submissions/{sub['id']}/review-details")
        assert resp.status_code == 200
        assert "transcript" in resp.json()

    # test_submission_service.py line 474: transcript fetch returns non-200 (warning)
    def test_review_details_transcript_non_200(self):
        tid = self._create_test()
        sub = client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": 301}).json()
        Mock = _mock_client(get_status=404)
        from src.config.settings import settings as svc_settings
        with patch("httpx.AsyncClient", Mock), \
             patch.object(svc_settings, "INTERVIEW_SERVICE_URL", "http://interview-svc"):
            resp = client.get(f"/v1/api/submissions/{sub['id']}/review-details")
        assert resp.status_code == 200
        assert resp.json()["transcript"] is None


# ---------------------------------------------------------------------------
# Quiz Session tests — covers quiz_session_route.py + quiz_session_schema.py
# ---------------------------------------------------------------------------

# Fake questions with correct_answers for scoring assertions
_QS = [
    {
        "id": f"q{i}",
        "question_type": "mcq",
        "difficulty": d,
        "question_text": f"Question {i}",
        "correct_answers": [1],
        "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
    }
    for i, d in enumerate(
        ["easy"] * 3 + ["medium"] * 4 + ["hard"] * 4, start=1
    )
]


async def _fake_fetch(question_service_url, test_id, config, exclude_ids):
    """Drop-in coroutine replacement for fetch_questions_for_part in route tests."""
    return _QS


class TestQuizSessions:
    def _create_test(self) -> int:
        return client.post(
            "/v1/api/tests/",
            json={"name": "QS Test", "test_type": "QUIZ", "number_of_questions": 11},
        ).json()["id"]

    def _create_submission(self, test_id: int) -> int:
        return client.post(
            "/v1/api/submissions/", json={"test_id": test_id, "user_id": 200}
        ).json()["id"]

    def _create_session(self, test_id: int, sub_id: int) -> dict:
        resp = client.post(
            "/v1/api/test-sessions/",
            json={"test_id": test_id, "submission_id": sub_id, "user_id": 200},
        )
        assert resp.status_code == 201
        return resp.json()

    # ------------------------------------------------------------------
    # POST /test-sessions/ — create_session
    # ------------------------------------------------------------------

    def test_create_session_returns_201_with_id(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        data = self._create_session(tid, sid)
        assert "id" in data
        assert data["status"] == "STARTED"

    def test_create_session_has_started_at(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        data = self._create_session(tid, sid)
        assert data["started_at"] is not None

    def test_create_session_current_part_is_a_for_started(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        status = client.get(f"/v1/api/test-sessions/{session['id']}/status").json()
        assert status["current_part"] == "A"

    def test_create_session_with_custom_part_a_config(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        resp = client.post(
            "/v1/api/test-sessions/",
            json={
                "test_id": tid,
                "submission_id": sid,
                "user_id": 200,
                "part_a_config": {"easy": 2, "medium": 3, "hard": 2},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["part_a_config"]["easy"] == 2

    # ------------------------------------------------------------------
    # GET /test-sessions/{session_id}
    # ------------------------------------------------------------------

    def test_get_session_by_id(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        resp = client.get(f"/v1/api/test-sessions/{session['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session["id"]

    def test_get_session_not_found_returns_404(self):
        resp = client.get("/v1/api/test-sessions/nonexistent-uuid-xxxx")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # GET /test-sessions/by-submission/{submission_id}
    # ------------------------------------------------------------------

    def test_get_session_by_submission(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        resp = client.get(f"/v1/api/test-sessions/by-submission/{sid}")
        assert resp.status_code == 200
        assert resp.json()["submission_id"] == sid
        assert resp.json()["id"] == session["id"]

    def test_get_session_by_submission_not_found_returns_404(self):
        resp = client.get("/v1/api/test-sessions/by-submission/99999")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # GET /test-sessions/{session_id}/status
    # ------------------------------------------------------------------

    def test_get_session_status(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        resp = client.get(f"/v1/api/test-sessions/{session['id']}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "STARTED"
        assert resp.json()["current_part"] == "A"

    def test_get_session_status_not_found_returns_404(self):
        resp = client.get("/v1/api/test-sessions/bad-id-xxx/status")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # GET /test-sessions/{session_id}/part-a/questions
    # ------------------------------------------------------------------

    def test_get_part_a_questions_returns_questions(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        assert resp.status_code == 200
        assert "questions" in resp.json()
        assert resp.json()["session_id"] == session["id"]

    def test_get_part_a_questions_strips_correct_answers(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        for q in resp.json()["questions"]:
            assert "correct_answers" not in q

    def test_get_part_a_questions_sets_status_in_progress(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        status_resp = client.get(f"/v1/api/test-sessions/{session['id']}/status")
        assert status_resp.json()["status"] == "PART_A_IN_PROGRESS"
        # from_orm: PART_A_IN_PROGRESS → current_part = "A" (covers schema line 62)
        assert status_resp.json()["current_part"] == "A"

    def test_get_part_a_questions_second_call_uses_cache(self):
        # First call fetches and caches; second call reads cache without calling _fetch_questions
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            r1 = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        # Second call — no mock; if it called _fetch_questions it would hit real service
        r2 = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        assert r2.status_code == 200
        assert len(r2.json()["questions"]) == len(r1.json()["questions"])

    def test_get_part_a_questions_wrong_status_returns_409(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        # Advance to PART_A_COMPLETED via submit
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        answers = [{"question_id": q["id"], "selected_answers": [1]} for q in _QS[:3]]
        client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        assert resp.status_code == 409

    def test_get_part_a_questions_not_found_returns_404(self):
        resp = client.get("/v1/api/test-sessions/no-such-id/part-a/questions")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # POST /test-sessions/{session_id}/part-a/submit
    # ------------------------------------------------------------------

    def _setup_part_a_in_progress(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            qresp = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        questions = qresp.json()["questions"]
        return session, questions

    def test_submit_part_a_returns_score(self):
        session, questions = self._setup_part_a_in_progress()
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        assert resp.status_code == 200
        assert "score" in resp.json()
        assert "correct_answers" in resp.json()

    def test_submit_part_a_all_correct_score_100(self):
        session, questions = self._setup_part_a_in_progress()
        # _QS has correct_answers=[1] for every question
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        assert resp.json()["score"] == 100.0

    def test_submit_part_a_all_wrong_score_0(self):
        session, questions = self._setup_part_a_in_progress()
        answers = [{"question_id": q["question_id"], "selected_answers": [2]} for q in questions]
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        assert resp.json()["score"] == 0.0
        assert resp.json()["correct_answers"] == 0

    def test_submit_part_a_sets_status_completed(self):
        session, questions = self._setup_part_a_in_progress()
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        status = client.get(f"/v1/api/test-sessions/{session['id']}/status").json()
        assert status["status"] == "PART_A_COMPLETED"
        # from_orm: PART_A_COMPLETED → current_part = "B" (covers schema line 64)
        assert status["current_part"] == "B"

    def test_submit_part_a_wrong_status_returns_409(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        # Status is STARTED — not PART_A_IN_PROGRESS
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": []},
        )
        assert resp.status_code == 409

    def test_submit_part_a_not_found_returns_404(self):
        resp = client.post(
            "/v1/api/test-sessions/no-such-id/part-a/submit",
            json={"session_id": "no-such-id", "answers": []},
        )
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # GET /test-sessions/{session_id}/part-b/questions
    # ------------------------------------------------------------------

    def _setup_part_a_completed(self, score_high=True):
        """Return session after Part A submitted with high or low score."""
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            qresp = client.get(f"/v1/api/test-sessions/{session['id']}/part-a/questions")
        questions = qresp.json()["questions"]
        # All correct → 100% score (high); all wrong → 0% (low)
        selected = [1] if score_high else [2]
        answers = [{"question_id": q["question_id"], "selected_answers": selected} for q in questions]
        client.post(
            f"/v1/api/test-sessions/{session['id']}/part-a/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        return session

    def test_get_part_b_questions_after_part_a(self):
        session = self._setup_part_a_completed(score_high=True)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        assert resp.status_code == 200
        assert "questions" in resp.json()
        assert resp.json()["session_id"] == session["id"]

    def test_get_part_b_questions_has_ai_message(self):
        # Adaptive message is always set — specific content depends on Part A score
        # which may not persist reliably through SQLite JSON round-trip in unit tests
        session = self._setup_part_a_completed(score_high=True)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        ai_message = resp.json()["ai_message"]
        assert ai_message is not None
        assert isinstance(ai_message, str)
        assert len(ai_message) > 0

    def test_get_part_b_questions_adaptive_message_is_one_of_known_strings(self):
        session = self._setup_part_a_completed(score_high=False)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        assert resp.json()["ai_message"] in [
            "Part B is calibrated to your performance. Keep going!",
            "Great work on Part A! Part B will challenge you further.",
        ]

    def test_get_part_b_questions_sets_status_in_progress(self):
        session = self._setup_part_a_completed()
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        status = client.get(f"/v1/api/test-sessions/{session['id']}/status").json()
        assert status["status"] == "PART_B_IN_PROGRESS"
        # from_orm: PART_B_IN_PROGRESS → current_part = "B" (covers schema line 64)
        assert status["current_part"] == "B"

    def test_get_part_b_questions_second_call_uses_cache(self):
        session = self._setup_part_a_completed()
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            r1 = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        r2 = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        assert r2.status_code == 200
        assert len(r2.json()["questions"]) == len(r1.json()["questions"])

    def test_get_part_b_questions_wrong_status_returns_409(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        # STARTED → not allowed for Part B
        resp = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        assert resp.status_code == 409

    def test_get_part_b_questions_not_found_returns_404(self):
        resp = client.get("/v1/api/test-sessions/no-such-id/part-b/questions")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # POST /test-sessions/{session_id}/part-b/submit
    # ------------------------------------------------------------------

    def _setup_part_b_in_progress(self, score_high=True):
        session = self._setup_part_a_completed(score_high=score_high)
        with patch("src.services.quiz_session_service.fetch_questions_for_part", new=_fake_fetch):
            qresp = client.get(f"/v1/api/test-sessions/{session['id']}/part-b/questions")
        questions = qresp.json()["questions"]
        return session, questions

    def test_submit_part_b_returns_final_score(self):
        session, questions = self._setup_part_b_in_progress()
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-b/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        assert resp.status_code == 200
        assert "score" in resp.json()
        assert "analysis" in resp.json()

    def test_submit_part_b_sets_status_completed(self):
        session, questions = self._setup_part_b_in_progress()
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        client.post(
            f"/v1/api/test-sessions/{session['id']}/part-b/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        status = client.get(f"/v1/api/test-sessions/{session['id']}/status").json()
        assert status["status"] == "COMPLETED"
        # from_orm: COMPLETED → current_part = None (covers schema line 67)
        assert status["current_part"] is None

    def test_submit_part_b_final_score_is_average_of_parts(self):
        # Both parts all-correct → 100% + 100% / 2 = 100%
        session, questions = self._setup_part_b_in_progress(score_high=True)
        answers = [{"question_id": q["question_id"], "selected_answers": [1]} for q in questions]
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-b/submit",
            json={"session_id": session["id"], "answers": answers},
        )
        assert resp.json()["score"] == 100.0

    def test_submit_part_b_wrong_status_returns_409(self):
        tid = self._create_test()
        sid = self._create_submission(tid)
        session = self._create_session(tid, sid)
        resp = client.post(
            f"/v1/api/test-sessions/{session['id']}/part-b/submit",
            json={"session_id": session["id"], "answers": []},
        )
        assert resp.status_code == 409

    def test_submit_part_b_not_found_returns_404(self):
        resp = client.post(
            "/v1/api/test-sessions/no-such-id/part-b/submit",
            json={"session_id": "no-such-id", "answers": []},
        )
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # fetch_questions_for_part internal paths (service layer)
    # ------------------------------------------------------------------

    def test_fetch_questions_no_url_returns_empty_list(self):
        from src.services.quiz_session_service import fetch_questions_for_part
        result = asyncio.run(fetch_questions_for_part(None, 1, {"easy": 3}, []))
        assert result == []

    def test_fetch_questions_with_url_and_list_response(self):
        from src.services.quiz_session_service import fetch_questions_for_part
        fake_qs = [
            {"id": f"q{i}", "type": "mcq", "difficulty": "easy",
             "question_text": f"Q{i}", "correct_answer": 1, "options": []}
            for i in range(5)
        ]

        class _FakeResp:
            status_code = 200
            def json(self): return fake_qs

        class _FakeClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **kw): return _FakeResp()

        with patch("httpx.AsyncClient", _FakeClient):
            result = asyncio.run(fetch_questions_for_part("http://q-svc", 1, {"easy": 3}, []))
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_fetch_questions_with_url_and_dict_response(self):
        from src.services.quiz_session_service import fetch_questions_for_part
        fake_qs = [
            {"id": f"q{i}", "type": "mcq", "difficulty": "easy",
             "question_text": f"Q{i}", "correct_answer": 0, "options": []}
            for i in range(5)
        ]

        class _FakeDictResp:
            status_code = 200
            def json(self): return {"questions": fake_qs}

        class _FakeDictClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **kw): return _FakeDictResp()

        with patch("httpx.AsyncClient", _FakeDictClient):
            result = asyncio.run(fetch_questions_for_part("http://q-svc", 1, {"easy": 3}, []))
        assert isinstance(result, list)
        assert len(result) <= 3

    def test_fetch_questions_non_200_raises_503(self):
        from src.services.quiz_session_service import fetch_questions_for_part
        from fastapi import HTTPException

        class _FailResp:
            status_code = 503
            text = "unavailable"
            def json(self): return {}

        class _FailClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **kw): return _FailResp()

        with patch("httpx.AsyncClient", _FailClient):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(fetch_questions_for_part("http://q-svc", 1, {"easy": 3}, []))
        assert exc_info.value.status_code == 503

    def test_fetch_questions_network_error_raises_503(self):
        from src.services.quiz_session_service import fetch_questions_for_part
        from fastapi import HTTPException
        import httpx

        class _ErrClient:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            async def get(self, *a, **kw): raise httpx.RequestError("network down")

        with patch("httpx.AsyncClient", _ErrClient):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(fetch_questions_for_part("http://q-svc", 1, {"easy": 3}, []))
        assert exc_info.value.status_code == 503
