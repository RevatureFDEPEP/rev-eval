"""GET /reports/user/{id} + /attempts — aggregates, filters, pagination, sort.

Seeded fixture (tests/conftest.py): user 42 has two SUBMITTED attempts
(50% in 1800s, 100% in 1200s), one ACTIVE with a partial answer, one EXPIRED
with none; user 7 has a SUBMITTED 80% attempt that must never leak in.
"""
from tests.conftest import S1, S2, S3, S4, USER

SUMMARY = f"/v1/api/reports/user/{USER}"
ATTEMPTS = f"/v1/api/reports/user/{USER}/attempts"


# ---- summary envelope ----

async def test_summary_aggregates_submitted_attempts_only(client):
    resp = await client.get(SUMMARY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER
    assert body["total_attempts"] == 2  # ACTIVE + EXPIRED excluded
    assert body["avg_score"] == 75.0    # (50 + 100) / 2
    assert body["best_score"] == 100.0
    assert body["total_time_seconds"] == 3000.0  # 1800 + 1200


async def test_summary_most_recent_is_latest_submitted(client):
    body = (await client.get(SUMMARY)).json()
    recent = body["most_recent"]
    assert recent["session_id"] == str(S2)
    assert recent["test_id"] == 2
    assert recent["test_name"] == "Python Data Structures Quiz"
    assert recent["score"] == 100.0
    assert recent["submitted_at"].startswith("2026-06-03T09:20")


async def test_summary_zero_attempts_is_zeroed_envelope_not_404(client):
    resp = await client.get("/v1/api/reports/user/999")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "user_id": 999,
        "total_attempts": 0,
        "avg_score": None,
        "best_score": None,
        "total_time_seconds": None,
        "most_recent": None,
    }


# ---- attempts: envelope + default sort ----

async def test_attempts_envelope_and_default_sort(client):
    resp = await client.get(ATTEMPTS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert body["page"] == 1
    assert body["size"] == 20
    # submitted_at desc, NULLs (ACTIVE/EXPIRED) last, then session_id.
    assert [i["session_id"] for i in body["items"]] == [
        str(S2), str(S1), str(S3), str(S4)
    ]


async def test_attempts_item_shape_and_score_semantics(client):
    items = {i["session_id"]: i for i in (await client.get(ATTEMPTS)).json()["items"]}
    s1 = items[str(S1)]
    assert s1["test_name"] == "Java Fundamentals Quiz"
    assert s1["status"] == "SUBMITTED"
    assert s1["score"] == 50.0
    assert s1["duration_seconds"] == 1800.0
    # ACTIVE session has a partial answer in the bank — score must be null.
    s3 = items[str(S3)]
    assert s3["status"] == "ACTIVE"
    assert s3["score"] is None
    assert s3["submitted_at"] is None and s3["duration_seconds"] is None
    # EXPIRED, never answered.
    assert items[str(S4)]["score"] is None


async def test_attempts_never_leak_other_users(client):
    body = (await client.get(ATTEMPTS)).json()
    assert {i["session_id"] for i in body["items"]} == {
        str(S1), str(S2), str(S3), str(S4)
    }


# ---- attempts: filters ----

async def test_filter_by_test_id(client):
    body = (await client.get(ATTEMPTS, params={"test_id": 1})).json()
    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {str(S1), str(S3)}


async def test_filter_by_status(client):
    body = (await client.get(ATTEMPTS, params={"status": "SUBMITTED"})).json()
    assert body["total"] == 2
    assert {i["session_id"] for i in body["items"]} == {str(S1), str(S2)}


async def test_filter_by_date_range_bounds_start_time(client):
    # started_at dates: S4=05-20, S1=06-01, S2=06-03, S3=06-05
    body = (
        await client.get(ATTEMPTS, params={"from": "2026-06-01", "to": "2026-06-03"})
    ).json()
    assert {i["session_id"] for i in body["items"]} == {str(S1), str(S2)}
    body = (await client.get(ATTEMPTS, params={"from": "2026-06-04"})).json()
    assert {i["session_id"] for i in body["items"]} == {str(S3)}
    body = (await client.get(ATTEMPTS, params={"to": "2026-05-31"})).json()
    assert {i["session_id"] for i in body["items"]} == {str(S4)}


async def test_filters_combine(client):
    body = (
        await client.get(ATTEMPTS, params={"test_id": 2, "status": "SUBMITTED"})
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["session_id"] == str(S2)


# ---- attempts: pagination ----

async def test_pagination_slices_and_reports_meta(client):
    page1 = (await client.get(ATTEMPTS, params={"size": 2, "page": 1})).json()
    page2 = (await client.get(ATTEMPTS, params={"size": 2, "page": 2})).json()
    assert page1["total"] == page2["total"] == 4
    assert (page1["page"], page1["size"]) == (1, 2)
    assert (page2["page"], page2["size"]) == (2, 2)
    assert [i["session_id"] for i in page1["items"]] == [str(S2), str(S1)]
    assert [i["session_id"] for i in page2["items"]] == [str(S3), str(S4)]


async def test_pagination_past_the_end_is_empty_with_total(client):
    body = (await client.get(ATTEMPTS, params={"size": 20, "page": 3})).json()
    assert body["items"] == []
    assert body["total"] == 4


# ---- attempts: sort ----

async def test_sort_by_score_asc_nulls_last(client):
    body = (await client.get(ATTEMPTS, params={"sort": "score:asc"})).json()
    assert [i["session_id"] for i in body["items"]] == [
        str(S1), str(S2), str(S3), str(S4)
    ]


async def test_sort_by_created_at_asc(client):
    body = (await client.get(ATTEMPTS, params={"sort": "created_at:asc"})).json()
    assert [i["session_id"] for i in body["items"]] == [
        str(S4), str(S1), str(S2), str(S3)
    ]


# ---- attempts: validation (422s) ----

async def test_rejects_unknown_sort_field_and_direction(client):
    assert (await client.get(ATTEMPTS, params={"sort": "user_id:asc"})).status_code == 422
    assert (await client.get(ATTEMPTS, params={"sort": "score:sideways"})).status_code == 422
    assert (await client.get(ATTEMPTS, params={"sort": "score"})).status_code == 422


async def test_rejects_out_of_range_page_and_size(client):
    assert (await client.get(ATTEMPTS, params={"page": 0})).status_code == 422
    assert (await client.get(ATTEMPTS, params={"size": 0})).status_code == 422
    assert (await client.get(ATTEMPTS, params={"size": 101})).status_code == 422


async def test_rejects_unknown_status(client):
    assert (await client.get(ATTEMPTS, params={"status": "DONE"})).status_code == 422
