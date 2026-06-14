"""Phase 3 regression tests: route authorization + submission IDOR guards.

Auth resolution (get_current_user_from_headers) and the DB session are
overridden, and service methods are patched, so the route-level authorization
logic is exercised in isolation. The ValueError->404 paths double as proof
that authorization passed before the service was reached.
"""
from datetime import datetime

import main
import pytest
from fastapi.testclient import TestClient
from src.db.session import get_db
from src.schemas.test_submission_schema import SubmissionStatus, TestSubmissionOut
from src.services.test_service import TestService
from src.services.test_submission_service import TestSubmissionService
from src.utils import dependencies as deps


@pytest.fixture
def client():
    c = TestClient(main.app)
    main.app.dependency_overrides[get_db] = lambda: object()
    yield c
    main.app.dependency_overrides.clear()


def _as(role, user_id=1):
    main.app.dependency_overrides[deps.get_current_user_from_headers] = lambda: {
        "id": user_id,
        "role": role,
        "email": f"{role.lower()}@example.com",
    }


def _sub_out(user_id):
    now = datetime.utcnow()
    return TestSubmissionOut(
        id=5,
        test_id=1,
        user_id=user_id,
        status=SubmissionStatus.ASSIGNED,
        assigned_at=now,
        created_at=now,
        updated_at=now,
    )


# --- Anonymous (no gateway headers) ------------------------------------------

def test_anonymous_submission_list_rejected(client):
    assert client.get("/v1/api/submissions/").status_code == 401


def test_anonymous_test_create_rejected(client):
    assert client.post("/v1/api/tests/", json={"name": "x"}).status_code == 401


# --- Test write routes --------------------------------------------------------

def test_participant_cannot_create_test(client):
    _as("PARTICIPANT")
    assert client.post("/v1/api/tests/", json={"name": "x"}).status_code == 403


def test_participant_cannot_update_test(client):
    _as("PARTICIPANT")
    assert client.put("/v1/api/tests/1/", json={"name": "x"}).status_code == 403


def test_participant_cannot_delete_test(client):
    _as("PARTICIPANT")
    assert client.delete("/v1/api/tests/1/").status_code == 403


def test_trainer_create_test_passes_authz(client, monkeypatch):
    _as("TRAINER", user_id=9)

    async def boom(*a, **k):
        raise RuntimeError("reached service")

    monkeypatch.setattr(TestService, "create_test", boom)
    # Trainer clears the authz gate: not 403. (Body validation / service error
    # may surface as 422/500, but never an authorization rejection.)
    assert client.post("/v1/api/tests/", json={"name": "x"}).status_code != 403


# --- Skill write routes -------------------------------------------------------

def test_participant_cannot_create_skill(client):
    _as("PARTICIPANT")
    assert client.post("/v1/api/skills/", json={"name": "py"}).status_code == 403


def test_participant_cannot_delete_skill(client):
    _as("PARTICIPANT")
    assert client.delete("/v1/api/skills/1/").status_code == 403


# --- Submission IDOR ----------------------------------------------------------

def test_participant_cannot_read_another_submission(client, monkeypatch):
    _as("PARTICIPANT", user_id=1)

    async def get_sub(db, sid):
        return _sub_out(user_id=2)  # owned by someone else

    monkeypatch.setattr(TestSubmissionService, "get_submission_by_id", get_sub)
    assert client.get("/v1/api/submissions/5/").status_code == 403


def test_participant_can_read_own_submission(client, monkeypatch):
    _as("PARTICIPANT", user_id=2)

    async def get_sub(db, sid):
        return _sub_out(user_id=2)

    monkeypatch.setattr(TestSubmissionService, "get_submission_by_id", get_sub)
    resp = client.get("/v1/api/submissions/5/")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == 2


def test_trainer_can_read_any_submission(client, monkeypatch):
    _as("TRAINER", user_id=99)

    async def get_sub(db, sid):
        return _sub_out(user_id=2)

    monkeypatch.setattr(TestSubmissionService, "get_submission_by_id", get_sub)
    assert client.get("/v1/api/submissions/5/").status_code == 200


def test_participant_cannot_bypass_ownership_via_query(client):
    _as("PARTICIPANT", user_id=1)
    assert client.get("/v1/api/submissions/?user_id=2").status_code == 403


def test_participant_list_pinned_to_self(client, monkeypatch):
    _as("PARTICIPANT", user_id=1)
    captured = {}

    async def by_user(db, uid):
        captured["uid"] = uid
        return []

    monkeypatch.setattr(TestSubmissionService, "list_submissions_by_user", by_user)
    resp = client.get("/v1/api/submissions/")
    assert resp.status_code == 200
    assert captured["uid"] == 1


def test_participant_cannot_update_submission(client):
    _as("PARTICIPANT", user_id=1)
    assert client.put("/v1/api/submissions/5/", json={"status": "GRADED"}).status_code == 403


def test_participant_cannot_delete_submission(client):
    _as("PARTICIPANT", user_id=1)
    assert client.delete("/v1/api/submissions/5/").status_code == 403


def test_trainer_update_submission_passes_authz(client, monkeypatch):
    _as("TRAINER", user_id=9)

    async def upd(db, sid, body):
        raise ValueError("not found")

    monkeypatch.setattr(TestSubmissionService, "update_submission", upd)
    # 404 (not 403) proves the trainer cleared the authz gate.
    assert client.put("/v1/api/submissions/5/", json={"status": "GRADED"}).status_code == 404


def test_participant_can_create_own_submission_only(client):
    _as("PARTICIPANT", user_id=1)
    # Creating for another user is forbidden.
    body_other = {"test_id": 1, "user_id": 2}
    assert client.post("/v1/api/submissions/", json=body_other).status_code == 403
