"""HTTP client for question-management-service.

The first cross-service call in the platform. Establishes the reusable
pattern (W3-F4 draft endpoint, W4 reporting): a module-level
``httpx.AsyncClient`` singleton with an explicit timeout, bounded retries on
transient failures only, and ``X-Correlation-Id`` propagation so a single
request can be traced across services in Loki (W2-F3).
"""
import asyncio
import logging
from typing import List, Optional

import httpx
from src.config.settings import settings
from src.utils.logging_config import get_correlation_id

logger = logging.getLogger(__name__)

# Explicit timeout: fail fast rather than hang a session-create request.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Bounded retries: 1 initial attempt + this many retries, transient errors only.
_MAX_RETRIES = 2
_BACKOFF_BASE = 0.2  # seconds; exponential per attempt

# Module-level singleton — reused across requests (connection pooling).
_client: Optional[httpx.AsyncClient] = None


class QuestionServiceError(Exception):
    """Raised when question-management-service cannot satisfy a request
    after bounded retries (or returns a non-retryable error)."""


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.QUESTION_SERVICE_URL, timeout=_TIMEOUT
        )
    return _client


async def aclose() -> None:
    """Close the singleton on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def sample_questions(size: int) -> List[dict]:
    """Fetch a random sample of `size` questions from question-management-service.

    Retries transient failures (network errors, timeouts, 5xx) with
    exponential backoff; never retries 4xx. Forwards the inbound correlation
    id on the outbound call.

    Returns the parsed question objects (full bodies — the caller is
    responsible for stripping answer fields before exposing them to a client).
    """
    client = get_client()
    headers = {"X-Correlation-Id": get_correlation_id()}
    last_exc: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = await client.get(
                "/v1/api/questions/sample",
                params={"size": size},
                headers=headers,
            )
        except httpx.TransportError as e:
            # Connect/read timeouts, connection errors — transient.
            last_exc = e
            logger.warning(
                "question-service sample transport error (attempt %d/%d): %s",
                attempt + 1, _MAX_RETRIES + 1, e,
            )
        else:
            if resp.status_code < 400:
                return resp.json()
            if resp.status_code < 500:
                # 4xx is a contract/client error — do not retry.
                raise QuestionServiceError(
                    f"question-service returned {resp.status_code}: {resp.text}"
                )
            # 5xx — transient, retry.
            last_exc = QuestionServiceError(
                f"question-service returned {resp.status_code}"
            )
            logger.warning(
                "question-service sample 5xx (attempt %d/%d): %s",
                attempt + 1, _MAX_RETRIES + 1, resp.status_code,
            )

        if attempt < _MAX_RETRIES:
            await asyncio.sleep(_BACKOFF_BASE * (2 ** attempt))

    raise QuestionServiceError(
        f"question-service unavailable after {_MAX_RETRIES + 1} attempts"
    ) from last_exc
