"""require_trainer gate tests (W4-F3).

These exercise the real dependency — no overrides — with real HS256 tokens
minted by the make_token fixture, hitting the app the way curl would. The
defense-in-depth tests bypass every frontend/gateway guard (spoofed X-User-*
headers, direct ASGI requests) and prove the gate only ever trusts the
verified token payload.

401 = no/invalid credentials; 403 = verified token, wrong role.
"""

AGGREGATE = "/v1/api/reports/aggregate"
QUESTIONS = "/v1/api/reports/test/1/questions"
TIMESERIES = "/v1/api/reports/timeseries"


async def test_missing_authorization_header_is_401(client):
    resp = await client.get(AGGREGATE)
    assert resp.status_code == 401


async def test_non_bearer_scheme_is_401(client):
    resp = await client.get(AGGREGATE, headers={"Authorization": "Basic abc123"})
    assert resp.status_code == 401


async def test_garbage_token_is_401(client):
    resp = await client.get(
        AGGREGATE, headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


async def test_wrong_signature_is_401(client, make_token):
    token = make_token("TRAINER", secret="some-other-signing-key")
    resp = await client.get(
        AGGREGATE, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_expired_token_is_401(client, make_token):
    token = make_token("TRAINER", expires_in=-60)
    resp = await client.get(
        AGGREGATE, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_participant_role_is_403(client, make_token):
    token = make_token("PARTICIPANT")
    resp = await client.get(
        AGGREGATE, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_admin_role_is_403(client, make_token):
    # Spec-strict: only the TRAINER claim passes; ADMIN is deliberately not
    # widened here (recorded decision in the W4-F3 plan).
    token = make_token("ADMIN")
    resp = await client.get(
        AGGREGATE, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_trainer_token_is_200(client, make_token):
    token = make_token("TRAINER")
    resp = await client.get(
        AGGREGATE, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


async def test_questions_endpoint_is_gated_too(client, make_token):
    assert (await client.get(QUESTIONS)).status_code == 401
    participant = make_token("PARTICIPANT")
    resp = await client.get(
        QUESTIONS, headers={"Authorization": f"Bearer {participant}"}
    )
    assert resp.status_code == 403
    trainer = make_token("TRAINER")
    resp = await client.get(
        QUESTIONS, headers={"Authorization": f"Bearer {trainer}"}
    )
    assert resp.status_code == 200


async def test_timeseries_endpoint_is_gated_too(client, make_token):
    assert (await client.get(TIMESERIES)).status_code == 401
    participant = make_token("PARTICIPANT")
    resp = await client.get(
        TIMESERIES, headers={"Authorization": f"Bearer {participant}"}
    )
    assert resp.status_code == 403
    trainer = make_token("TRAINER")
    resp = await client.get(
        TIMESERIES, headers={"Authorization": f"Bearer {trainer}"}
    )
    assert resp.status_code == 200


async def test_spoofed_gateway_headers_without_token_are_401(client):
    """Defense-in-depth: downstream services normally trust X-User-*; this
    gate must not — a curl straight to :8004 with spoofed headers fails."""
    resp = await client.get(
        AGGREGATE,
        headers={"X-User-Role": "TRAINER", "X-User-Id": "1"},
    )
    assert resp.status_code == 401


async def test_spoofed_gateway_headers_cannot_upgrade_participant(
    client, make_token
):
    """Role comes only from the verified token payload — spoofed X-User-Role
    headers alongside a real PARTICIPANT token still get 403."""
    token = make_token("PARTICIPANT")
    resp = await client.get(
        AGGREGATE,
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-Role": "TRAINER",
            "X-User-Id": "1",
        },
    )
    assert resp.status_code == 403


async def test_role_in_query_or_body_is_ignored(client, make_token):
    token = make_token("PARTICIPANT")
    resp = await client.get(
        AGGREGATE + "?role=TRAINER",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
