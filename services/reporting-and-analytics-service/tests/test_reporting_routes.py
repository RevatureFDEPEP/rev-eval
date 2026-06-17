"""HTTP-level tests: endpoint wiring, query-param parsing, pagination meta."""

SUMMARY = "/v1/api/reports/user/100"
ATTEMPTS = "/v1/api/reports/user/100/attempts"


class TestSummaryEndpoint:
    async def test_200_shape(self, client):
        r = await client.get(SUMMARY)
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == 100
        assert body["total_attempts"] == 4
        assert body["average_score"] == 0.4722
        assert body["best_score"] == 0.75
        assert body["total_time_spent_seconds"] == 900
        assert body["most_recent_attempt"]["session_id"] == "s2"

    async def test_unknown_user_empty_envelope(self, client):
        r = await client.get("/v1/api/reports/user/999")
        assert r.status_code == 200
        assert r.json()["total_attempts"] == 0
        assert r.json()["most_recent_attempt"] is None


class TestAttemptsEndpoint:
    async def test_pagination_meta(self, client):
        r = await client.get(ATTEMPTS, params={"page": 1, "size": 2})
        assert r.status_code == 200
        body = r.json()
        assert (body["page"], body["size"], body["total"]) == (1, 2, 4)
        assert [i["session_id"] for i in body["items"]] == ["s2", "s1"]

    async def test_status_filter(self, client):
        r = await client.get(ATTEMPTS, params={"status": "SUBMITTED", "size": 10})
        assert r.status_code == 200
        assert body_ids(r) == {"s1", "s2"}

    async def test_test_id_filter(self, client):
        r = await client.get(ATTEMPTS, params={"test_id": 1, "size": 10})
        assert body_ids(r) == {"s1", "s3", "s4"}

    async def test_date_range_inclusive_and_exclusive(self, client):
        # all attempts are dated 2026-06-16
        within = await client.get(
            ATTEMPTS, params={"from": "2026-06-16", "to": "2026-06-16", "size": 10}
        )
        assert within.json()["total"] == 4
        after = await client.get(ATTEMPTS, params={"from": "2026-06-17", "size": 10})
        assert after.json()["total"] == 0

    async def test_malformed_sort_is_422(self, client):
        # missing direction violates the field:direction pattern
        r = await client.get(ATTEMPTS, params={"sort": "submitted_at"})
        assert r.status_code == 422

    async def test_size_over_max_is_422(self, client):
        r = await client.get(ATTEMPTS, params={"size": 101})
        assert r.status_code == 422

    async def test_unknown_sort_field_falls_back_to_default(self, client):
        # well-formed but non-sortable field → default submitted_at order, not 500
        r = await client.get(ATTEMPTS, params={"sort": "score:desc", "size": 10})
        assert r.status_code == 200
        assert [i["session_id"] for i in r.json()["items"]] == ["s2", "s1", "s3", "s4"]


def body_ids(response) -> set:
    return {i["session_id"] for i in response.json()["items"]}
