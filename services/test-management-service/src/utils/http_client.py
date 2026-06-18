"""
Singleton httpx.AsyncClient for test-management-service.

Call get_http_client() to obtain the shared client.
Call close_http_client() on application shutdown to release connections.
"""
from typing import Optional

import httpx

_client: Optional[httpx.AsyncClient] = None

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


def get_http_client() -> httpx.AsyncClient:
    """Return the process-wide httpx.AsyncClient, creating it on first call."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


async def close_http_client() -> None:
    """Close and discard the singleton client. Safe to call even if uninitialised."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
