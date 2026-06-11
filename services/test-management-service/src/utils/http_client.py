"""
Shared async HTTP client for service-to-service calls.

Provides explicit timeouts, bounded exponential-backoff retries on transient
errors, and automatic X-Correlation-ID propagation so every hop in a request
chain can be traced end-to-end.
"""
import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Status codes that are safe to retry (server-side transient failures)
_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
# Network-level exceptions that are safe to retry
_RETRYABLE_EXC = (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)


async def call_service(
    method: str,
    url: str,
    *,
    correlation_id: Optional[str] = None,
    timeout: float = 10.0,
    max_retries: int = 2,
    headers: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> httpx.Response:
    """
    Make an HTTP request to an internal service with retries and correlation-id.

    Retries up to `max_retries` times on transient failures (network errors or
    retryable HTTP status codes) using exponential back-off (0.5 s, 1 s, …).
    `X-Correlation-ID` is always sent; a new UUID is minted when the caller
    does not supply one.

    Raises the last `httpx.RequestError` after exhausting retries. Non-retryable
    HTTP responses are returned immediately regardless of status code.
    """
    cid = correlation_id or str(uuid.uuid4())
    merged_headers = dict(headers or {})
    merged_headers["X-Correlation-ID"] = cid

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method, url, headers=merged_headers, **kwargs
                )

            if response.status_code not in _RETRYABLE_STATUS or attempt == max_retries:
                return response

            wait = 0.5 * (2 ** attempt)
            logger.warning(
                "Retryable HTTP %s from %s — attempt %d/%d cid=%s, retrying in %.1fs",
                response.status_code,
                url,
                attempt + 1,
                max_retries + 1,
                cid,
                wait,
            )
            await asyncio.sleep(wait)

        except _RETRYABLE_EXC as exc:
            last_exc = exc
            if attempt == max_retries:
                raise
            wait = 0.5 * (2 ** attempt)
            logger.warning(
                "Network error calling %s — attempt %d/%d cid=%s: %s, retrying in %.1fs",
                url,
                attempt + 1,
                max_retries + 1,
                cid,
                exc,
                wait,
            )
            await asyncio.sleep(wait)

    raise last_exc  # unreachable; satisfies type checkers
