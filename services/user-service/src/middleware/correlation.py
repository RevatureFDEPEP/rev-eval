"""X-Correlation-Id middleware for distributed log tracing.

Reads the X-Correlation-Id header from the incoming request (generating a
uuid4 hex when absent), stores it in the logging ContextVar so every log
line emitted during the request carries it, and echoes it back on the
response so callers can surface the id.

Header-only: it never touches the request body stream (the gateway
re-reads `await request.body()` downstream).

Propagate the id on outbound httpx calls with:
    headers={"X-Correlation-Id": get_correlation_id()}
"""

from uuid import uuid4

from src.utils.logging_config import set_correlation_id
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_HEADER = "X-Correlation-Id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get(CORRELATION_HEADER) or uuid4().hex
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
