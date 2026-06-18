import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
MAX_ATTEMPTS = 3
RETRY_STATUSES = {502, 503, 504}


async def call_service(
    url: str,
    method: str = "GET",
    *,
    correlation_id: str,
    json: dict | None = None,
    timeout: httpx.Timeout | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> httpx.Response:
    """
    Call a downstream service with explicit timeout, bounded retries, and
    correlation-ID header propagation.

    Retries on ConnectError, TimeoutException, and HTTP 502/503/504.
    Non-retryable responses (400, 404, 500, etc.) are returned immediately.
    Raises httpx.ConnectError if all attempts are exhausted.
    """
    effective_timeout = timeout or DEFAULT_TIMEOUT

    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=effective_timeout) as client:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    headers={"X-Correlation-Id": correlation_id},
                )
            if response.status_code not in RETRY_STATUSES:
                return response
            logger.warning(
                "[%s] Retryable HTTP %s from %s (attempt %d/%d)",
                correlation_id, response.status_code, url, attempt + 1, max_attempts,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning(
                "[%s] Transport error calling %s (attempt %d/%d): %s",
                correlation_id, url, attempt + 1, max_attempts, exc,
            )

        if attempt < max_attempts - 1:
            await asyncio.sleep(0.5 * (2 ** attempt))

    raise httpx.ConnectError(
        f"Service at {url} unavailable after {max_attempts} attempts"
    )
