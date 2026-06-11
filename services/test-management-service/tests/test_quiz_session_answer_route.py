"""Route-contract tests for POST /sessions/{id}/answer.

These cover request validation that happens before the service runs — notably
the required Idempotency-Key header — so they use dependency overrides and need
neither a database nor question-management-service.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.db.session import get_db
from src.utils.dependencies import get_current_participant_id
from src.v1.routes.quiz_session_route import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    async def _fake_db():
        yield None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_participant_id] = lambda: 1
    return TestClient(app)


def test_answer_requires_idempotency_key():
    """A submit with no Idempotency-Key header is rejected at validation (422)."""
    resp = _client().post(
        "/sessions/abc/answer",
        json={"question_id": "q0", "submitted_answers": [1]},
    )
    assert resp.status_code == 422


def test_answer_rejects_blank_idempotency_key():
    """An empty Idempotency-Key is treated as missing (422), not as a real key."""
    resp = _client().post(
        "/sessions/abc/answer",
        json={"question_id": "q0", "submitted_answers": [1]},
        headers={"Idempotency-Key": ""},
    )
    assert resp.status_code == 422
