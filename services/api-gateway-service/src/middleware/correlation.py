from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.utils.logging_config import set_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or uuid4().hex
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response
