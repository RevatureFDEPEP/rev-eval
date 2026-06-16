import httpx
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
