"""Regression tests: the gateway passes downstream responses through unchanged.

A downstream DELETE returning 204 No Content used to become a gateway 500,
because the proxy called resp.json() on an empty body labelled
application/json.
"""
import os
import time
from unittest.mock import AsyncMock, patch

import httpx
import jwt as pyjwt
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci-tests")
os.environ.setdefault("SERVICE_NAME", "api-gateway-service")

from main import app  # noqa: E402
from src.proxy import build_proxy_response  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def _auth_header() -> dict:
    token = pyjwt.encode(
        {"sub": "1", "email": "trainer@test.com", "role": "TRAINER", "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _downstream(response: httpx.Response):
    return patch("httpx.AsyncClient.request", new=AsyncMock(return_value=response))


class TestGatewayPassThrough:
    def test_delete_204_is_preserved_without_body(self):
        upstream = httpx.Response(204, headers={"content-type": "application/json"})
        with _downstream(upstream):
            resp = client.delete("/v1/api/tests/42/", headers=_auth_header())
        assert resp.status_code == 204
        assert resp.content == b""
        assert "content-type" not in resp.headers
        assert "x-request-id" in resp.headers

    def test_non_json_body_with_json_content_type_is_not_parsed(self):
        upstream = httpx.Response(
            502, content=b"upstream exploded", headers={"content-type": "application/json"}
        )
        with _downstream(upstream):
            resp = client.get("/v1/api/tests", headers=_auth_header())
        assert resp.status_code == 502
        assert resp.content == b"upstream exploded"

    def test_plain_text_body_and_content_type_pass_through(self):
        upstream = httpx.Response(
            200, content=b"id,score\n1,90\n", headers={"content-type": "text/csv; charset=utf-8"}
        )
        with _downstream(upstream):
            resp = client.get("/v1/api/reports/export", headers=_auth_header())
        assert resp.status_code == 200
        assert resp.text == "id,score\n1,90\n"
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert resp.headers["content-length"] == str(len(resp.content))

    def test_json_body_is_forwarded_byte_for_byte(self):
        body = b'{"id": 7, "name": "Python basics"}'
        upstream = httpx.Response(201, content=body, headers={"content-type": "application/json"})
        with _downstream(upstream):
            resp = client.post("/v1/api/tests", json={"name": "x"}, headers=_auth_header())
        assert resp.status_code == 201
        assert resp.content == body
        assert resp.headers["content-type"] == "application/json"

    def test_public_auth_route_preserves_status_and_body(self):
        upstream = httpx.Response(401, content=b"", headers={"content-type": "application/json"})
        with _downstream(upstream):
            resp = client.post("/v1/api/auth/login", json={"email": "a", "password": "b"})
        assert resp.status_code == 401
        assert resp.content == b""


class TestBuildProxyResponse:
    def test_hop_by_hop_and_gateway_owned_headers_are_dropped(self):
        upstream = httpx.Response(
            200,
            content=b"ok",
            headers={
                "content-type": "text/plain",
                "connection": "keep-alive",
                "transfer-encoding": "chunked",
                "x-request-id": "downstream-id",
                "access-control-allow-origin": "*",
                "vary": "Origin",
                "cache-control": "no-store",
                "location": "/v1/api/tests/7",
            },
        )
        resp = build_proxy_response(upstream)
        assert resp.status_code == 200
        assert resp.body == b"ok"
        assert resp.headers["content-type"] == "text/plain"
        assert resp.headers["cache-control"] == "no-store"
        assert resp.headers["location"] == "/v1/api/tests/7"
        for dropped in (
            "connection",
            "transfer-encoding",
            "x-request-id",
            "access-control-allow-origin",
            "vary",
        ):
            assert dropped not in resp.headers

    def test_304_has_no_body_or_length(self):
        upstream = httpx.Response(304, headers={"etag": '"abc"'})
        resp = build_proxy_response(upstream)
        assert resp.status_code == 304
        assert resp.body == b""
        assert resp.headers["etag"] == '"abc"'
        assert "content-length" not in resp.headers

    def test_repeated_headers_are_kept(self):
        upstream = httpx.Response(
            200, content=b"", headers=[("set-cookie", "a=1"), ("set-cookie", "b=2")]
        )
        resp = build_proxy_response(upstream)
        assert resp.headers.getlist("set-cookie") == ["a=1", "b=2"]
