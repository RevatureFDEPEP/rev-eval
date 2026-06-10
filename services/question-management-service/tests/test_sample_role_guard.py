"""Role gate for GET /questions/sample (W3-F7 item 4).

``GET /questions/sample`` returns full documents including ``correct_answers``
/ ``sample_answer``; before this guard any authenticated role could pull the
answer key of the whole bank through the gateway in one request.

Contract under test (``src.utils.authz.require_answer_key_role``):

* ``X-User-Role`` present and not TRAINER/ADMIN → 403 — the gateway always
  overwrites this header from the verified JWT, so it cannot be spoofed
  through the gateway.
* TRAINER / ADMIN → allowed.
* Header absent → allowed: an internal service-to-service call
  (test-management-service's session sampler sends only X-Correlation-Id).

The dependency is exercised over ASGI on a minimal FastAPI app rather than the
full router: the guard lives in its own module precisely so its tests don't
drag the whole route/service import graph into the coverage-gated measured
set. The live wiring on ``/questions/sample``
(``dependencies=[Depends(require_answer_key_role)]``) is exercised end-to-end
by the W3-F5 integration suite (header-less allow path, via the real
container) and was smoke-verified through the gateway (participant 403,
trainer 200).
"""
import httpx
from fastapi import Depends, FastAPI
from src.utils.authz import require_answer_key_role

app = FastAPI()


@app.get("/guarded", dependencies=[Depends(require_answer_key_role)])
async def guarded():
    return {"ok": True}


async def _get(headers=None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://qms-test") as c:
        return await c.get("/guarded", headers=headers or {})


async def test_participant_role_is_rejected_403():
    resp = await _get({"X-User-Role": "PARTICIPANT"})
    assert resp.status_code == 403


async def test_unknown_role_is_rejected_403():
    resp = await _get({"X-User-Role": "SOMETHING_ELSE"})
    assert resp.status_code == 403


async def test_trainer_role_is_allowed():
    resp = await _get({"X-User-Role": "TRAINER"})
    assert resp.status_code == 200


async def test_admin_role_is_allowed():
    resp = await _get({"X-User-Role": "ADMIN"})
    assert resp.status_code == 200


async def test_headerless_internal_call_is_allowed():
    """test-management-service calls /sample directly (no gateway, no role
    header) when minting a session — must keep working."""
    resp = await _get()
    assert resp.status_code == 200
