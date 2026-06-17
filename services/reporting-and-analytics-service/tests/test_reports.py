"""Route + role-guard tests with the upstream client mocked."""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TRAINER = {"X-User-Id": "1", "X-User-Role": "TRAINER"}
PARTICIPANT = {"X-User-Id": "5", "X-User-Role": "PARTICIPANT"}
PARTICIPANT_10 = {"X-User-Id": "10", "X-User-Role": "PARTICIPANT"}

SUBMISSIONS = [
    {"id": 1, "test_id": 1, "user_id": 10, "status": "GRADED",
     "final_score": 80, "ai_score": 70, "trainer_score": 80, "test": {"id": 1, "name": "Java"},
     "assigned_at": "2026-06-01T09:00:00", "submitted_at": "2026-06-02T10:00:00"},
    {"id": 2, "test_id": 1, "user_id": 11, "status": "ASSIGNED",
     "final_score": None, "ai_score": None, "trainer_score": None, "test": {"id": 1, "name": "Java"},
     "assigned_at": "2026-06-01T09:00:00", "submitted_at": None},
    {"id": 3, "test_id": 2, "user_id": 10, "status": "COMPLETED",
     "final_score": 60, "test": {"id": 2, "name": "SQL"},
     "assigned_at": "2026-06-03T09:00:00", "submitted_at": "2026-06-05T10:00:00"},
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


# --- candidate report (self or trainer/admin) ---------------------------------

def test_candidate_report_requires_auth_headers():
    assert client.get("/v1/api/reports/user/10").status_code == 401


def test_candidate_report_self_read_allowed():
    resp = client.get("/v1/api/reports/user/10", headers=PARTICIPANT_10)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == 10
    assert body["assigned"] == 2
    assert body["completed"] == 2
    assert body["in_progress"] == 0
    assert body["average_final_score"] == 70.0
    assert body["best_score"] == 80.0
    assert body["score"]["count"] == 2
    assert body["by_status"] == {"GRADED": 1, "COMPLETED": 1}


def test_candidate_report_participant_cannot_read_other():
    # Participant 5 may not read participant 10's report.
    assert client.get("/v1/api/reports/user/10", headers=PARTICIPANT).status_code == 403


def test_candidate_report_trainer_reads_any():
    resp = client.get("/v1/api/reports/user/10", headers=TRAINER)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == 10


# --- candidate attempts: pagination / filter / sort / score -------------------

def test_attempts_score_semantics_and_default_sort():
    # Default sort is submitted_at desc: SQL (06-05) before Java (06-02).
    resp = client.get("/v1/api/reports/user/10/attempts", headers=PARTICIPANT_10)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert [i["test_name"] for i in body["items"]] == ["SQL", "Java"]
    assert [i["score"] for i in body["items"]] == [60.0, 80.0]


def test_attempts_filter_by_status():
    resp = client.get(
        "/v1/api/reports/user/10/attempts",
        headers=PARTICIPANT_10,
        params={"status": "completed"},  # case-insensitive
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["test_name"] == "SQL"
    assert body["status"] == "completed"


def test_attempts_sort_by_score_desc():
    resp = client.get(
        "/v1/api/reports/user/10/attempts",
        headers=PARTICIPANT_10,
        params={"sort": "score", "order": "desc"},
    )
    assert [i["score"] for i in resp.json()["items"]] == [80.0, 60.0]


def test_attempts_pagination():
    page1 = client.get(
        "/v1/api/reports/user/10/attempts",
        headers=PARTICIPANT_10,
        params={"sort": "score", "order": "desc", "page": 1, "page_size": 1},
    ).json()
    assert page1["total"] == 2
    assert page1["page_size"] == 1
    assert len(page1["items"]) == 1
    assert page1["items"][0]["score"] == 80.0

    page2 = client.get(
        "/v1/api/reports/user/10/attempts",
        headers=PARTICIPANT_10,
        params={"sort": "score", "order": "desc", "page": 2, "page_size": 1},
    ).json()
    assert page2["items"][0]["score"] == 60.0


def test_attempts_participant_cannot_read_other():
    assert (
        client.get("/v1/api/reports/user/10/attempts", headers=PARTICIPANT).status_code
        == 403
    )
