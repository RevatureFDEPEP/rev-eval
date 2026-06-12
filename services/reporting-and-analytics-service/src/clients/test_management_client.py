"""HTTP client for test-management-service.

Reporting is a read-through aggregator: it pulls submissions and tests from
test-management-service over compose-internal DNS, with a bounded timeout. It
propagates the caller's gateway-verified identity (X-User-*) and a correlation
id so role-gated upstream endpoints authorize the call and requests stay
traceable. Upstream failures surface as 503 so a reporting hiccup never
masquerades as bad data.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from src.config.settings import settings

logger = logging.getLogger(__name__)


async def _get_json(path: str, headers: Optional[Dict[str, str]]) -> Any:
    url = f"{settings.TEST_MANAGEMENT_URL}{path}"
    try:
        async with httpx.AsyncClient(
            timeout=settings.UPSTREAM_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            response = await client.get(url, headers=headers or {})
    except httpx.RequestError as exc:
        logger.error("test-management-service unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="test-management-service is unreachable",
        )

    if response.status_code != 200:
        logger.error(
            "test-management-service returned %d for %s", response.status_code, path
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"test-management-service returned {response.status_code}",
        )
    return response.json()


async def list_submissions(
    headers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    data = await _get_json("/v1/api/submissions/", headers)
    return data if isinstance(data, list) else []


async def list_tests(headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    data = await _get_json("/v1/api/tests", headers)
    return data if isinstance(data, list) else []
