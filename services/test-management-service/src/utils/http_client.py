"""Process-level httpx.AsyncClient singleton for the question-management-service.

A single client is reused across requests so the connection pool is shared
(creating a fresh ``httpx.AsyncClient`` per request trashes the pool). The
client is lazily constructed on first use and closed on app shutdown via
``close_qms_client``. Timeouts are explicit — 2s to connect, 5s overall — so a
slow/hung qms cannot pin a request indefinitely.
"""

import httpx
from src.config.settings import settings

_qms_client: httpx.AsyncClient | None = None


def get_qms_client() -> httpx.AsyncClient:
    """Return the shared question-management-service httpx client (lazy init)."""
    global _qms_client
    if _qms_client is None:
        _qms_client = httpx.AsyncClient(
            base_url=settings.QUESTION_SERVICE_URL,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    return _qms_client


async def close_qms_client() -> None:
    """Close the shared client on shutdown (idempotent)."""
    global _qms_client
    if _qms_client is not None:
        await _qms_client.aclose()
        _qms_client = None
