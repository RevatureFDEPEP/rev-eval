import json
import logging
import sys

import pytest

from src.utils.logging_config import (
    JsonFormatter,
    get_correlation_id,
    set_correlation_id,
    setup_logging,
)


@pytest.fixture(autouse=True)
def _restore_root_logger():
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    root.handlers = saved_handlers
    root.setLevel(saved_level)


@pytest.fixture(autouse=True)
def _reset_correlation_id():
    set_correlation_id("-")
    yield
    set_correlation_id("-")


def _make_record(msg="hello", level=logging.INFO, name="test.logger"):
    return logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )


# ── JsonFormatter ──────────────────────────────────────────────────────────────


def test_formatter_emits_required_fields():
    formatter = JsonFormatter("api-gateway")
    output = json.loads(formatter.format(_make_record()))
    assert output["level"] == "INFO"
    assert output["service"] == "api-gateway"
    assert output["logger"] == "test.logger"
    assert output["message"] == "hello"
    assert "timestamp" in output
    assert "correlation_id" in output


def test_formatter_includes_extra_fields():
    formatter = JsonFormatter("api-gateway")
    record = _make_record()
    record.request_id = "req-abc"
    output = json.loads(formatter.format(record))
    assert output["request_id"] == "req-abc"


def test_formatter_includes_exc_info():
    formatter = JsonFormatter("api-gateway")
    try:
        raise ValueError("boom")
    except ValueError:
        exc = sys.exc_info()
    record = _make_record(level=logging.ERROR)
    record.exc_info = exc
    output = json.loads(formatter.format(record))
    assert "exc_info" in output
    assert "ValueError" in output["exc_info"]
    assert "boom" in output["exc_info"]


def test_formatter_uses_current_correlation_id():
    set_correlation_id("corr-xyz")
    formatter = JsonFormatter("api-gateway")
    output = json.loads(formatter.format(_make_record()))
    assert output["correlation_id"] == "corr-xyz"


def test_formatter_default_correlation_id_is_dash():
    formatter = JsonFormatter("api-gateway")
    output = json.loads(formatter.format(_make_record()))
    assert output["correlation_id"] == "-"


def test_formatter_output_is_valid_json():
    formatter = JsonFormatter("api-gateway")
    result = formatter.format(_make_record(msg='quote"here'))
    json.loads(result)  # must not raise


# ── setup_logging ──────────────────────────────────────────────────────────────


def test_setup_logging_installs_single_stdout_handler():
    setup_logging("api-gateway", "INFO")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)
    assert root.handlers[0].stream is sys.stdout


def test_setup_logging_respects_level():
    setup_logging("api-gateway", "DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_clears_uvicorn_handlers():
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addHandler(logging.StreamHandler())
    setup_logging("api-gateway", "INFO")
    assert uvicorn_logger.handlers == []
    assert uvicorn_logger.propagate is True


def test_setup_logging_clears_uvicorn_access_handlers():
    for name in ("uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.addHandler(logging.StreamHandler())
    setup_logging("api-gateway", "INFO")
    for name in ("uvicorn.error", "uvicorn.access"):
        assert logging.getLogger(name).handlers == []


# ── contextvar helpers ─────────────────────────────────────────────────────────


def test_get_correlation_id_default():
    assert get_correlation_id() == "-"


def test_set_and_get_correlation_id():
    set_correlation_id("test-id-123")
    assert get_correlation_id() == "test-id-123"
