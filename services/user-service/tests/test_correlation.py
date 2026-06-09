import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.correlation import CorrelationIdMiddleware
from src.utils.logging_config import get_correlation_id, set_correlation_id


@pytest.fixture(autouse=True)
def _reset_correlation_id():
    set_correlation_id("-")
    yield
    set_correlation_id("-")


def _make_client():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"correlation_id": get_correlation_id()}

    return TestClient(app)


# ── header propagation ─────────────────────────────────────────────────────────


def test_echoes_supplied_correlation_id():
    client = _make_client()
    resp = client.get("/ping", headers={"X-Correlation-Id": "supplied-id"})
    assert resp.status_code == 200
    assert resp.headers["x-correlation-id"] == "supplied-id"


def test_contextvar_set_to_supplied_id():
    client = _make_client()
    resp = client.get("/ping", headers={"X-Correlation-Id": "ctx-test"})
    assert resp.json()["correlation_id"] == "ctx-test"


# ── id generation when absent ──────────────────────────────────────────────────


def test_generates_id_when_header_absent():
    client = _make_client()
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert "x-correlation-id" in resp.headers


def test_generated_id_is_32_hex_no_dashes():
    client = _make_client()
    generated = client.get("/ping").headers["x-correlation-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated)


def test_generates_unique_id_per_request():
    client = _make_client()
    id1 = client.get("/ping").headers["x-correlation-id"]
    id2 = client.get("/ping").headers["x-correlation-id"]
    assert id1 != id2


def test_contextvar_reflects_generated_id():
    client = _make_client()
    resp = client.get("/ping")
    header_id = resp.headers["x-correlation-id"]
    body_id = resp.json()["correlation_id"]
    assert header_id == body_id
