"""HTTP-level tests: endpoint wiring, authz gate, query parsing, pagination."""

SUMMARY = "/v1/api/reports/user/100"
ATTEMPTS = "/v1/api/reports/user/100/attempts"

# Gateway-injected identity headers (the platform auth contract).
SELF = {"X-User-Id": "100"}  # participant 100 reading their own reports
OTHER = {"X-User-Id": "200"}  # a different participant
TRAINER = {"X-User-Id": "200", "X-User-Role": "TRAINER"}  # trainer reads anyone


class TestAuthorization:
    async def test_self_allowed(self, client):
        assert (await client.get(SUMMARY, headers=SELF)).status_code == 200

    async def test_other_participant_forbidden(self, client):
        # IDOR guard: participant 200 may not read participant 100's reports
        assert (await client.get(SUMMARY, headers=OTHER)).status_code == 403
        assert (await client.get(ATTEMPTS, headers=OTHER)).status_code == 403

    async def test_trainer_reads_any_user(self, client):
        assert (await client.get(SUMMARY, headers=TRAINER)).status_code == 200

    async def test_missing_identity_forbidden(self, client):
        # No gateway headers (e.g. bypassing the gateway) → denied
        assert (await client.get(SUMMARY)).status_code == 403


class TestSummaryEndpoint:
    async def test_200_shape(self, client):
        r = await client.get(SUMMARY, headers=SELF)
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == 100
        assert body["total_attempts"] == 4
        assert body["average_score"] == 0.7083  # SUBMITTED-only
        assert body["best_score"] == 0.75
        assert body["total_time_spent_seconds"] == 900
        assert body["most_recent_attempt"]["session_id"] == "s2"

    async def test_unknown_user_empty_envelope(self, client):
        # trainer can query any user; user 999 has no attempts
        r = await client.get("/v1/api/reports/user/999", headers=TRAINER)
        assert r.status_code == 200
        assert r.json()["total_attempts"] == 0
        assert r.json()["most_recent_attempt"] is None


class TestAttemptsEndpoint:
    async def test_pagination_meta(self, client):
        r = await client.get(ATTEMPTS, params={"page": 1, "size": 2}, headers=SELF)
        assert r.status_code == 200
        body = r.json()
        assert (body["page"], body["size"], body["total"]) == (1, 2, 4)
        assert [i["session_id"] for i in body["items"]] == ["s2", "s1"]

    async def test_status_filter(self, client):
        r = await client.get(
            ATTEMPTS, params={"status": "SUBMITTED", "size": 10}, headers=SELF
        )
        assert r.status_code == 200
        assert body_ids(r) == {"s1", "s2"}

    async def test_test_id_filter(self, client):
        r = await client.get(ATTEMPTS, params={"test_id": 1, "size": 10}, headers=SELF)
        assert body_ids(r) == {"s1", "s3", "s4"}

    async def test_date_range_inclusive_and_exclusive(self, client):
        within = await client.get(
            ATTEMPTS,
            params={"from": "2026-06-16", "to": "2026-06-16", "size": 10},
            headers=SELF,
        )
        assert within.json()["total"] == 4
        after = await client.get(
            ATTEMPTS, params={"from": "2026-06-17", "size": 10}, headers=SELF
        )
        assert after.json()["total"] == 0

    async def test_malformed_sort_is_422(self, client):
        # missing direction violates the field:direction pattern
        r = await client.get(ATTEMPTS, params={"sort": "submitted_at"}, headers=SELF)
        assert r.status_code == 422

    async def test_unknown_sort_field_is_422(self, client):
        # well-formed but non-sortable field is rejected, not silently ignored
        r = await client.get(ATTEMPTS, params={"sort": "score:desc"}, headers=SELF)
        assert r.status_code == 422

    async def test_size_over_max_is_422(self, client):
        r = await client.get(ATTEMPTS, params={"size": 101}, headers=SELF)
        assert r.status_code == 422


def body_ids(response) -> set:
    return {i["session_id"] for i in response.json()["items"]}
