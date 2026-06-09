import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

RESERVED_LOG_RECORD_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    correlation_id_ctx.set(value)


def _json_default(value: Any) -> str:
    return str(value)


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        for key, value in record.__dict__.items():
            if key not in RESERVED_LOG_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=_json_default, separators=(",", ":"))


def setup_logging(service_name: str, level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
