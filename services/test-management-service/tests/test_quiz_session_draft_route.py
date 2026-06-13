"""Route-contract tests for PATCH /sessions/{id}/draft.

Cover request validation and the service-error → HTTP-status mapping using
dependency overrides + a patched service, so they need neither a database nor
question-management-service.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.db.session import get_db
from src.schemas.quiz_session_schema import DraftSaveResponse
from src.services.quiz_session_service import QuizSessionError
from src.utils.dependencies import get_current_participant_id
from src.v1.routes.quiz_session_route import router

SAVE_DRAFT = "src.v1.routes.quiz_session_route.QuizSessionService.save_draft"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    async def _fake_db():
        yield None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_participant_id] = lambda: 1
    return TestClient(app)


def test_draft_requires_answers_body():
    """A PATCH with no `answers` field is rejected at validation (422)."""
    resp = _client().patch("/sessions/abc/draft", json={})
    assert resp.status_code == 422


def test_draft_rejects_oversized_payload_422():
    """An over-cap answer map is rejected at validation before reaching the
    service, so an advisory autosave can't persist an unbounded blob."""
    oversized = {f"q{i}": [1] for i in range(201)}  # > _MAX_DRAFT_QUESTIONS
    with patch(SAVE_DRAFT, new_callable=AsyncMock) as save:
        resp = _client().patch("/sessions/abc/draft", json={"answers": oversized})
    assert resp.status_code == 422
    save.assert_not_called()


def test_draft_rejects_too_many_options_per_question_422():
    with patch(SAVE_DRAFT, new_callable=AsyncMock) as save:
        resp = _client().patch(
            "/sessions/abc/draft",
            json={"answers": {"q1": list(range(51))}},  # > _MAX_OPTIONS_PER_QUESTION
        )
    assert resp.status_code == 422
    save.assert_not_called()


def test_draft_rejects_negative_option_id_422():
    with patch(SAVE_DRAFT, new_callable=AsyncMock) as save:
        resp = _client().patch("/sessions/abc/draft", json={"answers": {"q1": [-1]}})
    assert resp.status_code == 422
    save.assert_not_called()


def test_draft_happy_path_returns_ack():
    ack = DraftSaveResponse(
        session_id="abc",
        status="ACTIVE",
        current_index=2,
        saved_at=datetime(2026, 6, 12, 10, 0, 0),
    )
    with patch(SAVE_DRAFT, new_callable=AsyncMock, return_value=ack):
        resp = _client().patch("/sessions/abc/draft", json={"answers": {"q2": [1]}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_index"] == 2
    assert body["status"] == "ACTIVE"


def test_draft_missing_session_maps_404():
    with patch(SAVE_DRAFT, new_callable=AsyncMock, side_effect=ValueError("nope")):
        resp = _client().patch("/sessions/abc/draft", json={"answers": {"q2": [1]}})
    assert resp.status_code == 404


def test_draft_wrong_user_maps_403():
    with patch(
        SAVE_DRAFT,
        new_callable=AsyncMock,
        side_effect=QuizSessionError("forbidden", status_code=403),
    ):
        resp = _client().patch("/sessions/abc/draft", json={"answers": {"q2": [1]}})
    assert resp.status_code == 403


def test_draft_inactive_session_maps_409():
    with patch(
        SAVE_DRAFT,
        new_callable=AsyncMock,
        side_effect=QuizSessionError("not active", status_code=409),
    ):
        resp = _client().patch("/sessions/abc/draft", json={"answers": {"q2": [1]}})
    assert resp.status_code == 409
