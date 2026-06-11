# src/utils/http_client.py
"""Shared httpx.AsyncClient singleton for service-to-service calls.

W3-F1 spec (line 48) mandates a singleton client with an explicit timeout
rather than spinning up a fresh client per request — connection pooling is
reused across calls and a hung downstream cannot stall a request forever.
"""
import httpx

# Explicit timeout: connect + read + write + pool, all bounded.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return the process-wide AsyncClient, lazily created."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


async def close_http_client() -> None:
    """Dispose the singleton (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
