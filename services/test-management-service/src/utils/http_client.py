import httpx
from fastapi import HTTPException
from src.config.settings import settings

_qms_client: httpx.AsyncClient | None = None


def get_qms_client() -> httpx.AsyncClient:
    """Return a reused AsyncClient pointed at question-management-service."""
    global _qms_client
    if _qms_client is None or _qms_client.is_closed:
        _qms_client = httpx.AsyncClient(
            base_url=settings.QUESTION_SERVICE_URL,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    return _qms_client


async def fetch_question(question_id: str, correlation_id: str = "") -> dict:
    """Service-to-service fetch; includes correct_answers — never forwarded to client."""
    client = get_qms_client()
    try:
        resp = await client.get(
            f"/v1/api/questions/{question_id}",
            headers={"X-Correlation-Id": correlation_id} if correlation_id else {},
        )
    except Exception as exc:
        raise HTTPException(502, detail=f"Question service error: {exc}") from exc
    if resp.status_code == 404:
        raise HTTPException(404, detail=f"Question {question_id} not found")
    resp.raise_for_status()
    return resp.json()
