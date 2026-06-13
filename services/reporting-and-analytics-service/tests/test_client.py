"""Tests for the test-management HTTP client (httpx mocked)."""
import httpx
import pytest
from fastapi import HTTPException
from src.clients import test_management_client as tm


class _FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


class _FakeClient:
    """Minimal async-context-manager stand-in for httpx.AsyncClient."""

    def __init__(self, *, response=None, error=None):
        self._response = response
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        if self._error:
            raise self._error
        return self._response


def _patch_client(monkeypatch, *, response=None, error=None):
    monkeypatch.setattr(
        tm.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeClient(response=response, error=error),
    )


@pytest.mark.asyncio
async def test_list_submissions_success(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, [{"id": 1}]))
    assert await tm.list_submissions({"X-Correlation-Id": "cid-1"}) == [{"id": 1}]


@pytest.mark.asyncio
async def test_list_tests_non_list_response_coerced_to_empty(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(200, {"oops": True}))
    assert await tm.list_tests() == []


@pytest.mark.asyncio
async def test_upstream_non_200_raises_503(monkeypatch):
    _patch_client(monkeypatch, response=_FakeResponse(500))
    with pytest.raises(HTTPException) as exc:
        await tm.list_submissions()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_upstream_unreachable_raises_503(monkeypatch):
    _patch_client(monkeypatch, error=httpx.RequestError("boom"))
    with pytest.raises(HTTPException) as exc:
        await tm.list_tests()
    assert exc.value.status_code == 503
