"""Phase 3 regression: question mutation routes require trainer/admin.

Mounts the question router on a throwaway app and patches the service layer,
so authorization is exercised without MongoDB or the full app settings.
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.question_service import QuestionService
from src.utils.dependencies import require_question_editor
from src.v1.routes import question_routes


@pytest.fixture
def client(monkeypatch):
    async def fake_create(question):
        return "new-id"

    async def fake_update(qid, body):
        return True

    async def fake_delete(qid):
        return True

    monkeypatch.setattr(QuestionService, "create_question", fake_create)
    monkeypatch.setattr(QuestionService, "update_question", fake_update)
    monkeypatch.setattr(QuestionService, "delete_question", fake_delete)

    app = FastAPI()
    app.include_router(question_routes.router, prefix="/v1/api")
    return TestClient(app)


_BODY = {"type": "true_false", "question_text": "The sky is blue?", "correct_answers": [True]}


def test_create_question_rejects_anonymous(client):
    assert client.post("/v1/api/questions/", json=_BODY).status_code == 401


def test_create_question_rejects_participant(client):
    resp = client.post("/v1/api/questions/", json=_BODY, headers={"X-User-Role": "PARTICIPANT"})
    assert resp.status_code == 403


def test_create_question_allows_trainer(client):
    resp = client.post("/v1/api/questions/", json=_BODY, headers={"X-User-Role": "TRAINER"})
    assert resp.status_code == 201


def test_update_question_rejects_participant(client):
    resp = client.put("/v1/api/questions/abc", json={"question_text": "x"}, headers={"X-User-Role": "PARTICIPANT"})
    assert resp.status_code == 403


def test_delete_question_rejects_anonymous(client):
    assert client.delete("/v1/api/questions/abc").status_code == 401


def test_delete_question_allows_admin(client):
    resp = client.delete("/v1/api/questions/abc", headers={"X-User-Role": "ADMIN"})
    assert resp.status_code == 200


def test_require_question_editor_unit():
    from fastapi import HTTPException

    assert require_question_editor("trainer") == "TRAINER"
    assert require_question_editor("ADMIN") == "ADMIN"
    with pytest.raises(HTTPException) as anon:
        require_question_editor(None)
    assert anon.value.status_code == 401
    with pytest.raises(HTTPException) as part:
        require_question_editor("PARTICIPANT")
    assert part.value.status_code == 403
