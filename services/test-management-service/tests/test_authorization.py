"""
Authorization tests for test-management-service.

Authentication proves who the caller is (their own Bearer JWT, resolved through
user-service); authorization decides what they may do (trainer or participant);
ownership decides which test, submission or quiz session they may touch.

Each denied write also checks the stored row is unchanged.
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
import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from main import app
from src.config.settings import settings
from src.db.session import get_db, engine, Base
from src.models.test import Test
from src.models.skill import Skill
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission
from src.models.quiz_session import QuizSession
from src.utils.dependencies import get_current_user

TestingAsyncSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_create_tables())


async def override_get_db():
    async with TestingAsyncSession() as db:
        yield db


TRAINER_A = {"id": 9001, "email": "trainer-a@test.com", "role": "TRAINER"}
TRAINER_B = {"id": 9002, "email": "trainer-b@test.com", "role": "TRAINER"}
ALICE = {"id": 9101, "email": "alice@test.com", "role": "PARTICIPANT"}
BOB = {"id": 9102, "email": "bob@test.com", "role": "PARTICIPANT"}

_CALLER = {"user": TRAINER_A}


async def override_get_current_user():
    return _CALLER["user"]


def act_as(user):
    _CALLER["user"] = user


client = TestClient(app)


@pytest.fixture(autouse=True)
def _identity():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    act_as(TRAINER_A)
    yield


def _row(model, pk):
    async def run():
        async with TestingAsyncSession() as db:
            return await db.get(model, pk)
    return asyncio.run(run())


def _count(model, *where):
    async def run():
        async with TestingAsyncSession() as db:
            return len((await db.execute(select(model).where(*where))).scalars().all())
    return asyncio.run(run())


def _new_test(trainer=TRAINER_A, name="Authz Quiz"):
    act_as(trainer)
    resp = client.post("/v1/api/tests/", json={"name": name, "test_type": "QUIZ", "number_of_questions": 11})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _assign(test_id, participant, trainer=TRAINER_A):
    act_as(trainer)
    resp = client.post("/v1/api/submissions/", json={"test_id": test_id, "user_id": participant["id"]})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _evaluated(submission_id, trainer=TRAINER_A):
    """Move a submission to EVALUATED (AI scoring done), ready for trainer review."""
    act_as(trainer)
    resp = client.put(f"/v1/api/submissions/{submission_id}/", json={"status": "EVALUATED"})
    assert resp.status_code == 200, resp.text


def _start(test_id, submission_id, participant):
    act_as(participant)
    resp = client.post("/v1/api/test-sessions/", json={
        "test_id": test_id, "submission_id": submission_id, "user_id": participant["id"],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Authentication: the real dependency, no override
# ---------------------------------------------------------------------------

def _token(sub, role="PARTICIPANT", secret=None):
    return jwt.encode(
        {"sub": str(sub), "role": role, "email": "x@test.com", "exp": int(time.time()) + 600},
        secret or settings.JWT_SECRET,
        algorithm="HS256",
    )


class _UserServiceStub:
    """Stands in for user-service: records each lookup and returns that user."""

    seen = []

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def get(self, url, headers=None, **kwargs):
        _UserServiceStub.seen.append((url, dict(headers or {})))
        user_id = int(url.rstrip("/").rsplit("/", 1)[-1])

        class R:
            status_code = 200

            @staticmethod
            def json():
                return {"id": user_id, "email": f"u{user_id}@test.com", "role": "PARTICIPANT"}

        return R()


class TestAuthentication:
    @pytest.fixture(autouse=True)
    def _real_identity(self):
        app.dependency_overrides.pop(get_current_user, None)
        _UserServiceStub.seen = []
        yield
        app.dependency_overrides[get_current_user] = override_get_current_user

    def test_missing_token_is_401(self):
        assert client.get("/v1/api/submissions/").status_code == 401

    def test_invalid_token_is_401(self):
        bad = _token(ALICE["id"], secret="not-the-secret")
        resp = client.get("/v1/api/submissions/", headers={"Authorization": f"Bearer {bad}"})
        assert resp.status_code == 401

    def test_identity_headers_alone_are_not_authentication(self):
        resp = client.get("/v1/api/submissions/", headers={"X-User-Id": "1", "X-User-Role": "TRAINER"})
        assert resp.status_code == 401

    def test_spoofed_identity_headers_are_ignored(self):
        token = _token(ALICE["id"])
        with patch("httpx.AsyncClient", _UserServiceStub):
            resp = client.get(
                "/v1/api/submissions/",
                headers={"Authorization": f"Bearer {token}", "X-User-Id": "1", "X-User-Email": "t@test.com"},
            )
        assert resp.status_code == 200
        url, headers = _UserServiceStub.seen[0]
        assert url.endswith(f"/v1/api/users/{ALICE['id']}")
        assert headers.get("Authorization") == f"Bearer {token}"


# ---------------------------------------------------------------------------
# Tests: trainers manage their own tests; participants read assigned ones
# ---------------------------------------------------------------------------

class TestTestsAuthorization:
    def test_participant_cannot_create_test(self):
        act_as(ALICE)
        before = _count(Test)
        resp = client.post("/v1/api/tests/", json={"name": "Mine", "test_type": "QUIZ"})
        assert resp.status_code == 403
        assert _count(Test) == before

    def test_participant_cannot_update_or_delete_test(self):
        tid = _new_test()
        act_as(ALICE)
        assert client.put(f"/v1/api/tests/{tid}/", json={"name": "Hijacked"}).status_code == 403
        assert client.delete(f"/v1/api/tests/{tid}/").status_code == 403
        row = _row(Test, tid)
        assert row is not None and row.name == "Authz Quiz"

    def test_other_trainer_cannot_update_or_delete_test(self):
        tid = _new_test(TRAINER_A)
        act_as(TRAINER_B)
        assert client.put(f"/v1/api/tests/{tid}/", json={"name": "Hijacked"}).status_code == 403
        assert client.delete(f"/v1/api/tests/{tid}/").status_code == 403
        assert _row(Test, tid).name == "Authz Quiz"

    def test_participant_sees_only_assigned_tests(self):
        assigned = _new_test(name="Assigned")
        other = _new_test(name="Not assigned")
        _assign(assigned, ALICE)
        act_as(ALICE)
        ids = {t["id"] for t in client.get("/v1/api/tests/").json()}
        assert assigned in ids and other not in ids
        assert client.get(f"/v1/api/tests/{assigned}/").status_code == 200
        assert client.get(f"/v1/api/tests/{other}/").status_code == 403

    def test_participant_cannot_list_by_creator_or_other_users_tests(self):
        act_as(ALICE)
        assert client.get(f"/v1/api/tests/created-by/{TRAINER_A['id']}/").status_code == 403
        assert client.get(f"/v1/api/tests/submissions-by/{BOB['id']}/").status_code == 403
        assert client.get(f"/v1/api/tests/submissions-by/{ALICE['id']}/").status_code == 200

    def test_trainer_reads_creator_listing(self):
        tid = _new_test()
        resp = client.get(f"/v1/api/tests/created-by/{TRAINER_A['id']}/")
        assert resp.status_code == 200
        assert tid in {t["id"] for t in resp.json()}


# ---------------------------------------------------------------------------
# Skills: everyone signed in reads, only trainers change
# ---------------------------------------------------------------------------

class TestSkillsAuthorization:
    def test_participant_reads_but_cannot_change_skills(self):
        skill = client.post("/v1/api/skills/", json={"name": f"authz-skill-{time.time_ns()}"})
        assert skill.status_code == 201
        sid = skill.json()["id"]
        act_as(ALICE)
        assert client.get("/v1/api/skills/").status_code == 200
        assert client.post("/v1/api/skills/", json={"name": "participant-skill"}).status_code == 403
        assert client.put(f"/v1/api/skills/{sid}/", json={"name": "renamed"}).status_code == 403
        assert client.delete(f"/v1/api/skills/{sid}/").status_code == 403
        assert _row(Skill, sid).name == skill.json()["name"]
        assert _count(Skill, Skill.name == "participant-skill") == 0


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

class TestSubmissionsAuthorization:
    def test_participant_lists_only_own_and_cannot_change_user_id(self):
        tid = _new_test()
        mine = _assign(tid, ALICE)
        _assign(tid, BOB)
        act_as(ALICE)
        own = client.get("/v1/api/submissions/")
        assert own.status_code == 200
        assert mine in {s["id"] for s in own.json()}
        assert all(s["user_id"] == ALICE["id"] for s in own.json())
        assert client.get(f"/v1/api/submissions/?user_id={BOB['id']}").status_code == 403
        assert client.get(f"/v1/api/submissions/?user_id={ALICE['id']}").status_code == 200

    def test_participant_cannot_read_another_users_submission(self):
        tid = _new_test()
        bobs = _assign(tid, BOB)
        alices = _assign(tid, ALICE)
        act_as(ALICE)
        assert client.get(f"/v1/api/submissions/{bobs}/").status_code == 403
        assert client.get(f"/v1/api/submissions/{alices}/").status_code == 200

    def test_participant_cannot_create_update_or_delete_submissions(self):
        tid = _new_test()
        mine = _assign(tid, ALICE)
        act_as(ALICE)
        before = _count(TestSubmission)
        assert client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": ALICE["id"]}).status_code == 403
        assert _count(TestSubmission) == before
        resp = client.put(f"/v1/api/submissions/{mine}/", json={"final_score": 100, "status": "GRADED"})
        assert resp.status_code == 403
        row = _row(TestSubmission, mine)
        assert row.final_score is None and row.status.value == "ASSIGNED"
        assert client.delete(f"/v1/api/submissions/{mine}/").status_code == 403
        assert _row(TestSubmission, mine) is not None

    def test_participant_cannot_bulk_assign(self):
        tid = _new_test()
        act_as(ALICE)
        before = _count(TestSubmission)
        resp = client.post(
            "/v1/api/submissions/bulk-assign",
            json={"test_id": tid, "participant_emails": ["someone@test.com"]},
        )
        assert resp.status_code == 403
        assert _count(TestSubmission) == before

    def test_other_trainer_cannot_assign_or_grade_on_my_test(self):
        tid = _new_test(TRAINER_A)
        sub = _assign(tid, ALICE)
        act_as(TRAINER_B)
        before = _count(TestSubmission)
        assert client.post("/v1/api/submissions/", json={"test_id": tid, "user_id": BOB["id"]}).status_code == 403
        assert client.post(
            "/v1/api/submissions/bulk-assign", json={"test_id": tid, "participant_emails": ["x@test.com"]}
        ).status_code == 403
        assert _count(TestSubmission) == before
        assert client.post(f"/v1/api/submissions/{sub}/trainer-review", json={"trainer_score": 90}).status_code == 403
        assert client.get(f"/v1/api/submissions/{sub}/review-details").status_code == 403
        row = _row(TestSubmission, sub)
        assert row.trainer_score is None and row.reviewed_by_id is None

    def test_participant_cannot_use_review_surfaces_or_grade(self):
        tid = _new_test()
        sub = _assign(tid, ALICE)
        act_as(ALICE)
        for path in ("/v1/api/submissions/trainer/evaluated", "/v1/api/submissions/trainer/all",
                     "/v1/api/submissions/graded", f"/v1/api/submissions/{sub}/review-details"):
            assert client.get(path).status_code == 403, path
        resp = client.post(f"/v1/api/submissions/{sub}/trainer-review", json={"trainer_score": 100})
        assert resp.status_code == 403
        row = _row(TestSubmission, sub)
        assert row.trainer_score is None and row.final_score is None and row.status.value == "ASSIGNED"

    def test_trainer_reviews_a_submission_on_own_test(self):
        tid = _new_test()
        sub = _assign(tid, ALICE)
        _evaluated(sub)
        resp = client.post(f"/v1/api/submissions/{sub}/trainer-review", json={"trainer_score": 88})
        assert resp.status_code == 200, resp.text
        row = _row(TestSubmission, sub)
        assert row.trainer_score == 88 and row.reviewed_by_id == TRAINER_A["id"]

    def test_graded_list_is_limited_to_managed_tests(self):
        mine = _new_test(TRAINER_A, name="A graded")
        theirs = _new_test(TRAINER_B, name="B graded")
        my_sub = _assign(mine, ALICE, TRAINER_A)
        their_sub = _assign(theirs, ALICE, TRAINER_B)
        _evaluated(my_sub, TRAINER_A)
        _evaluated(their_sub, TRAINER_B)
        act_as(TRAINER_A)
        client.post(f"/v1/api/submissions/{my_sub}/trainer-review", json={"trainer_score": 70})
        act_as(TRAINER_B)
        client.post(f"/v1/api/submissions/{their_sub}/trainer-review", json={"trainer_score": 80})
        act_as(TRAINER_A)
        ids = {s["id"] for s in client.get("/v1/api/submissions/graded").json()}
        assert my_sub in ids and their_sub not in ids


# ---------------------------------------------------------------------------
# Quiz sessions
# ---------------------------------------------------------------------------

class TestQuizSessionAuthorization:
    def test_participant_cannot_start_a_session_for_someone_else(self):
        tid = _new_test()
        bobs = _assign(tid, BOB)
        act_as(ALICE)
        before = _count(QuizSession)
        # Bob's submission, claimed as Alice
        resp = client.post("/v1/api/test-sessions/", json={"test_id": tid, "submission_id": bobs, "user_id": ALICE["id"]})
        assert resp.status_code == 403
        # Bob's submission, with Bob's user_id
        resp = client.post("/v1/api/test-sessions/", json={"test_id": tid, "submission_id": bobs, "user_id": BOB["id"]})
        assert resp.status_code == 403
        assert _count(QuizSession) == before

    def test_session_must_match_the_submissions_test(self):
        tid = _new_test()
        other = _new_test(name="Other quiz")
        mine = _assign(tid, ALICE)
        act_as(ALICE)
        resp = client.post("/v1/api/test-sessions/", json={"test_id": other, "submission_id": mine, "user_id": ALICE["id"]})
        assert resp.status_code == 403

    def test_participant_cannot_operate_on_another_participants_session(self):
        tid = _new_test()
        bobs_session = _start(tid, _assign(tid, BOB), BOB)
        act_as(ALICE)
        for path in (f"/v1/api/test-sessions/{bobs_session}",
                     f"/v1/api/test-sessions/{bobs_session}/status",
                     f"/v1/api/test-sessions/{bobs_session}/part-a/questions",
                     f"/v1/api/test-sessions/{bobs_session}/part-b/questions"):
            assert client.get(path).status_code == 403, path
        assert client.patch(
            f"/v1/api/test-sessions/{bobs_session}/draft", json={"answers": [{"question_id": "q1", "selected_answers": [1]}]}
        ).status_code == 403
        assert client.post(
            f"/v1/api/test-sessions/{bobs_session}/part-a/submit", json={"session_id": bobs_session, "answers": []}
        ).status_code == 403
        assert client.post(
            f"/v1/api/test-sessions/{bobs_session}/part-b/submit", json={"session_id": bobs_session, "answers": []}
        ).status_code == 403
        row = _row(QuizSession, bobs_session)
        assert row.status.value == "STARTED" and row.draft_answers is None and row.part_a_score is None

    def test_participant_cannot_read_session_by_another_users_submission(self):
        tid = _new_test()
        bobs_sub = _assign(tid, BOB)
        _start(tid, bobs_sub, BOB)
        act_as(ALICE)
        assert client.get(f"/v1/api/test-sessions/by-submission/{bobs_sub}").status_code == 403

    def test_owner_and_managing_trainer_can_read_the_session(self):
        tid = _new_test(TRAINER_A)
        sub = _assign(tid, ALICE)
        session = _start(tid, sub, ALICE)
        assert client.get(f"/v1/api/test-sessions/{session}/status").status_code == 200
        act_as(TRAINER_A)
        assert client.get(f"/v1/api/test-sessions/by-submission/{sub}").status_code == 200
        act_as(TRAINER_B)
        assert client.get(f"/v1/api/test-sessions/by-submission/{sub}").status_code == 403
        assert client.get(f"/v1/api/test-sessions/{session}").status_code == 403

    def test_trainer_cannot_take_a_participants_quiz(self):
        tid = _new_test(TRAINER_A)
        session = _start(tid, _assign(tid, ALICE), ALICE)
        act_as(TRAINER_A)
        assert client.patch(f"/v1/api/test-sessions/{session}/draft", json={"answers": [{"question_id": "q", "selected_answers": [0]}]}).status_code == 403
        assert _row(QuizSession, session).draft_answers is None

    def test_owner_saves_a_draft(self):
        tid = _new_test()
        session = _start(tid, _assign(tid, ALICE), ALICE)
        questions = [
            {"id": f"q{i}", "type": "mcq", "question_text": f"Q{i}?", "difficulty": d,
             "options": [{"option_id": 0, "text": "A"}, {"option_id": 1, "text": "B"}], "correct_answer": 0}
            for i, d in enumerate(["easy"] * 3 + ["medium"] * 4 + ["hard"] * 4)
        ]
        with patch("src.services.quiz_session_service.fetch_questions_for_part",
                   new_callable=AsyncMock, return_value=questions):
            assert client.get(f"/v1/api/test-sessions/{session}/part-a/questions").status_code == 200
        resp = client.patch(f"/v1/api/test-sessions/{session}/draft", json={"answers": [{"question_id": "q1", "selected_answers": [2]}]})
        assert resp.status_code == 200, resp.text
        assert _row(QuizSession, session).draft_answers is not None
