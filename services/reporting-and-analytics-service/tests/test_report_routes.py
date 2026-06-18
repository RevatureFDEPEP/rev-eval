"""Route-level tests for the reporting endpoints via FastAPI TestClient."""
from tests.conftest import USER_ID

# ── GET /reports/user/{user_id} ───────────────────────────────────────────────


def test_summary_endpoint_returns_correct_aggregates(client):
    resp = client.get(f"/reports/user/{USER_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER_ID
    assert body["total_attempts"] == 4
    assert body["average_score"] == 72.5
    assert body["best_score"] == 90.0
    assert body["total_time_spent"] == 750
    assert body["most_recent_attempt"]["session_id"] == "a4"


def test_summary_endpoint_empty_user(client):
    resp = client.get("/reports/user/99999")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_attempts"] == 0
    assert body["most_recent_attempt"] is None


# ── GET /reports/user/{user_id}/attempts ──────────────────────────────────────


def test_attempts_endpoint_default_pagination_meta(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert body["page"] == 1
    assert body["size"] == 20
    assert body["pages"] == 1
    assert len(body["items"]) == 4


def test_attempts_endpoint_pagination(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?page=1&size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert body["size"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 2


def test_attempts_endpoint_size_over_max_is_rejected(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?size=101")
    assert resp.status_code == 422


def test_attempts_endpoint_filter_by_test_id(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?test_id=t1")
    body = resp.json()
    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {"a1", "a2"}


def test_attempts_endpoint_filter_by_status(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?status=COMPLETED")
    body = resp.json()
    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {"a1", "a4"}


def test_attempts_endpoint_filter_by_date_range(client):
    resp = client.get(
        f"/reports/user/{USER_ID}/attempts?from=2026-06-05&to=2026-06-10"
    )
    body = resp.json()
    # a2 (06-05) and a3 (06-10), both inclusive
    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {"a2", "a3"}


def test_attempts_endpoint_sort_by_score_desc(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?sort=score:desc")
    body = resp.json()
    scores = [i["score"] for i in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_attempts_endpoint_invalid_sort_pattern_is_422(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?sort=score-desc")
    assert resp.status_code == 422


def test_attempts_endpoint_unknown_sort_field_is_400(client):
    resp = client.get(f"/reports/user/{USER_ID}/attempts?sort=bogus:desc")
    assert resp.status_code == 400


# ── CORS / health ─────────────────────────────────────────────────────────────


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_cors_allows_frontend_origin(client):
    resp = client.get(
        f"/reports/user/{USER_ID}",
        headers={"Origin": "http://localhost:3000"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
