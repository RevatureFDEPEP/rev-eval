"""Standard JSON log formatting for rev-eval services.

setup_logging() routes every log record (including uvicorn's) through a
single stdout handler that emits one JSON object per line. Promtail parses
these lines and ships them to Loki, where fields like `level` and
`correlation_id` become queryable.

The correlation id is carried in a ContextVar set per-request by
src/middleware/correlation.py; logs emitted outside a request (startup,
init_db, seed scripts) fall back to "-".
"""

import json
import logging
import sys
from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    correlation_id_ctx.set(correlation_id)


class JsonFormatter(logging.Formatter):
    """Render each record as a single-line JSON object for Loki ingestion."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """Configure root + uvicorn loggers to emit JSON to stdout.

    Idempotent. Call once at module import in main.py AND again in the
    FastAPI startup event: uvicorn (CLI or uvicorn.run) installs its own
    plain-text handlers *after* main.py is imported, so the startup-event
    call strips them and restores JSON-only output without duplicates.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
