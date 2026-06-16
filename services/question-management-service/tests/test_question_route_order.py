"""Phase 2 test: static question routes must not be shadowed by GET /{id}."""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.question_service import QuestionService
from src.v1.routes import question_routes


@pytest.fixture
def client(monkeypatch):
    async def fake_filter(**kwargs):
        return []

    async def fake_by_tags(tags, limit):
        return []

    async def fake_get_by_id(qid):
        # If routing is wrong, /filter or /by-tags would land here with that
        # literal as the id — fail loudly so the test catches the regression.
        raise AssertionError(f"get_question_by_id wrongly received id={qid!r}")

    monkeypatch.setattr(QuestionService, "filter_questions", fake_filter)
    monkeypatch.setattr(QuestionService, "find_by_tags", fake_by_tags)
    monkeypatch.setattr(QuestionService, "get_question_by_id", fake_get_by_id)

    app = FastAPI()
    app.include_router(question_routes.router, prefix="/v1/api")
    return TestClient(app)


def test_filter_route_not_shadowed(client):
    resp = client.get("/v1/api/questions/filter?type=mcq")
    assert resp.status_code == 200
    assert resp.json() == []


def test_by_tags_route_not_shadowed(client):
    resp = client.get("/v1/api/questions/by-tags?tags=java")
    assert resp.status_code == 200
    assert resp.json() == []


def test_real_id_still_reaches_get_by_id(client, monkeypatch):
    # A genuine id must still route to get_by_id (404 when missing).
    async def missing(qid):
        return None

    monkeypatch.setattr(QuestionService, "get_question_by_id", missing)
    resp = client.get("/v1/api/questions/64b7f0c2a1e4d5f6a7b8c9d0")
    assert resp.status_code == 404
