"""Route-level RBAC contract for the manual-grade endpoint (W5-F1).

POST /v1/api/sessions/{id}/answers/{index}/grade is trainer-gated
(get_current_trainer, the W4-F3 pattern): 401 without auth headers, 403 for a
non-trainer, 200 for a trainer. The grading service is patched for the 200 path
(no DB).
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.db.session import get_db
from src.schemas.grading_schema import GradedAnswerOut, GradingQueueOut
from src.utils.dependencies import get_current_trainer, get_current_user_from_headers
from src.v1.routes.session_route import router

SID = uuid4()
URL = f"/v1/api/sessions/{SID}/answers/1/grade"

# Mount only the session router on a minimal app — never `main` — so collecting
# this module doesn't pull every other service into the coverage denominator
# (the lean-app pattern used by test_answer_endpoint's route test).
_app = FastAPI()
_app.include_router(router, prefix="/v1/api")


def _client():
    _app.dependency_overrides[get_db] = lambda: None
    return TestClient(_app, raise_server_exceptions=False)


def _override(dep, value):
    _app.dependency_overrides[dep] = value


def teardown_function():
    _app.dependency_overrides.clear()


def test_grade_requires_auth_headers_401():
    client = _client()
    resp = client.post(URL, json={"score": 0.5})
    assert resp.status_code == 401


def test_grade_forbidden_for_participant_403():
    _override(get_current_user_from_headers, lambda: {"id": 5, "role": "PARTICIPANT"})
    resp = _client().post(URL, json={"score": 0.5})
    assert resp.status_code == 403


def test_grade_ok_for_trainer_200():
    _override(get_current_trainer, lambda: {"id": 9, "role": "TRAINER"})
    graded = GradedAnswerOut(
        answer_id=7,
        session_id=SID,
        question_index=1,
        score=0.75,
        is_correct=False,
        grading_status="GRADED",
        feedback="ok",
        graded_by_id=9,
        graded_at=None,
        session_needs_grading=False,
    )
    with patch(
        "src.v1.routes.session_route.GradingService.grade_answer",
        new_callable=AsyncMock,
    ) as grade:
        grade.return_value = graded
        resp = _client().post(URL, json={"score": 0.75, "feedback": "ok"})
    assert resp.status_code == 200
    assert resp.json()["grading_status"] == "GRADED"
    assert resp.json()["session_needs_grading"] is False


def test_grading_queue_forbidden_for_participant_403():
    _override(get_current_user_from_headers, lambda: {"id": 5, "role": "PARTICIPANT"})
    resp = _client().get("/v1/api/sessions/grading-queue")
    assert resp.status_code == 403


def test_grading_queue_ok_for_trainer_200():
    _override(get_current_trainer, lambda: {"id": 9, "role": "TRAINER"})
    queue = GradingQueueOut(items=[], total=0, page=1, size=20)
    with patch(
        "src.v1.routes.session_route.GradingService.list_queue",
        new_callable=AsyncMock,
    ) as lq:
        lq.return_value = queue
        resp = _client().get("/v1/api/sessions/grading-queue?test_id=1")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "page": 1, "size": 20}
