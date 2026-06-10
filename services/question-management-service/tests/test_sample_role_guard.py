"""Role gate on GET /questions/sample (W3-F7 item 4).

The endpoint returns full documents including ``correct_answers`` /
``sample_answer``; before this guard any authenticated role could pull the
answer key of the whole bank through the gateway in one request.

Contract under test (see ``require_answer_key_role``):

* ``X-User-Role`` present and not TRAINER/ADMIN → 403 — the gateway always
  overwrites this header from the verified JWT, so it cannot be spoofed
  through the gateway.
* TRAINER / ADMIN → allowed.
* Header absent → allowed: an internal service-to-service call
  (test-management-service's session sampler sends only X-Correlation-Id).

The app is driven over ASGI; ``QuestionService.sample_questions`` is patched
so no Mongo (real or mock) is involved — only the guard is under test.
"""
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from main import app

SAMPLE_URL = "/v1/api/questions/sample"


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://qms-test")


async def _get(client, headers=None):
    with patch(
        "src.v1.routes.question_routes.QuestionService.sample_questions",
        new_callable=AsyncMock,
    ) as sample:
        sample.return_value = []
        async with client as c:
            return await c.get(SAMPLE_URL, headers=headers or {})


async def test_participant_role_is_rejected_403(client):
    resp = await _get(client, {"X-User-Role": "PARTICIPANT"})
    assert resp.status_code == 403


async def test_unknown_role_is_rejected_403(client):
    resp = await _get(client, {"X-User-Role": "SOMETHING_ELSE"})
    assert resp.status_code == 403


async def test_trainer_role_is_allowed(client):
    resp = await _get(client, {"X-User-Role": "TRAINER"})
    assert resp.status_code == 200


async def test_admin_role_is_allowed(client):
    resp = await _get(client, {"X-User-Role": "ADMIN"})
    assert resp.status_code == 200


async def test_headerless_internal_call_is_allowed(client):
    """test-management-service calls /sample directly (no gateway, no role
    header) when minting a session — must keep working."""
    resp = await _get(client)
    assert resp.status_code == 200
