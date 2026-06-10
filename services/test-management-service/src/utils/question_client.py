"""
Singleton httpx.AsyncClient for calls to question-management-service.

A single long-lived client (with an explicit timeout) is reused across
requests so connections are pooled, rather than opening a new client per
call. Closed on app shutdown via close_question_client().
"""

import httpx

# Explicit timeout for all question-management-service calls.
QMS_TIMEOUT = 10.0

_client: httpx.AsyncClient | None = None


def get_question_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, creating it on first use."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=QMS_TIMEOUT)
    return _client


async def close_question_client() -> None:
    """Close the shared client (call on app shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
