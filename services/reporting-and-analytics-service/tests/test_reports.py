"""Route + role-guard tests with the upstream client mocked."""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TRAINER = {"X-User-Id": "1", "X-User-Role": "TRAINER"}
PARTICIPANT = {"X-User-Id": "5", "X-User-Role": "PARTICIPANT"}

SUBMISSIONS = [
    {"id": 1, "test_id": 1, "user_id": 10, "status": "GRADED",
     "final_score": 80, "ai_score": 70, "trainer_score": 80, "test": {"id": 1, "name": "Java"}},
    {"id": 2, "test_id": 1, "user_id": 11, "status": "ASSIGNED",
     "final_score": None, "ai_score": None, "trainer_score": None, "test": {"id": 1, "name": "Java"}},
    {"id": 3, "test_id": 2, "user_id": 10, "status": "COMPLETED",
     "final_score": 60, "test": {"id": 2, "name": "SQL"}},
]
TESTS = [{"id": 1, "name": "Java"}, {"id": 2, "name": "SQL"}]


@pytest.fixture(autouse=True)
def _mock_upstream(monkeypatch):
    monkeypatch.setattr(
        "src.clients.test_management_client.list_submissions",
        AsyncMock(return_value=SUBMISSIONS),
    )
    monkeypatch.setattr(
        "src.clients.test_management_client.list_tests",
        AsyncMock(return_value=TESTS),
    )


# --- role guard ---------------------------------------------------------------

def test_overview_requires_auth_headers():
    assert client.get("/v1/api/reports/overview").status_code == 401


def test_overview_rejects_participant():
    assert client.get("/v1/api/reports/overview", headers=PARTICIPANT).status_code == 403


# --- overview -----------------------------------------------------------------

def test_overview_aggregates():
    resp = client.get("/v1/api/reports/overview", headers=TRAINER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tests"] == 2
    assert body["total_submissions"] == 3
    assert body["by_status"] == {"GRADED": 1, "ASSIGNED": 1, "COMPLETED": 1}
    assert body["completion_rate"] == pytest.approx(0.6667, abs=1e-3)
    assert body["score"]["count"] == 2  # the unscored ASSIGNED row is excluded
    assert body["score"]["average"] == 70.0


# --- per-test -----------------------------------------------------------------

def test_test_report_filters_and_names():
    resp = client.get("/v1/api/reports/tests/1", headers=TRAINER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["test_id"] == 1
    assert body["name"] == "Java"
    assert body["submission_count"] == 2
    assert body["completion_rate"] == 0.5
    assert body["score"]["count"] == 1
    assert body["score"]["average"] == 80.0


# --- per-participant ----------------------------------------------------------

def test_participant_report():
    resp = client.get("/v1/api/reports/participants/10", headers=TRAINER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == 10
    assert body["assigned"] == 2
    assert body["completed"] == 2
    assert body["average_final_score"] == 70.0
    assert {t["test_id"] for t in body["tests"]} == {1, 2}
