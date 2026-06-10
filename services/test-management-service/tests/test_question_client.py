"""Unit tests for the question-management-service httpx client.

The AsyncClient singleton is replaced with a mock; asyncio.sleep is patched
out so backoff adds no wall-clock delay. Covers the contract: success path +
correlation-id propagation, no-retry on 4xx, bounded retry on 5xx/transport
errors, and recovery when a transient failure is followed by success.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.utils import question_client
from src.utils.question_client import QuestionServiceError

CLIENT = "src.utils.question_client"


def _resp(status_code=200, payload=None, text=""):
    return SimpleNamespace(
        status_code=status_code, json=lambda: (payload or []), text=text
    )


def _drive(get_mock):
    """Run sample_questions with a mocked client + correlation id + no sleep."""
    client = MagicMock()
    client.get = get_mock
    with patch(f"{CLIENT}.get_client", return_value=client), \
         patch(f"{CLIENT}.get_correlation_id", return_value="cid-123"), \
         patch(f"{CLIENT}.asyncio.sleep", new_callable=AsyncMock):
        return asyncio.run(question_client.sample_questions(3)), client


def test_success_returns_parsed_payload():
    questions = [{"id": "q1", "type": "mcq"}]
    out, client = _drive(AsyncMock(return_value=_resp(200, questions)))
    assert out == questions
    assert client.get.await_count == 1


def test_forwards_correlation_id():
    out, client = _drive(AsyncMock(return_value=_resp(200, [])))
    _, kwargs = client.get.call_args
    assert kwargs["headers"]["X-Correlation-Id"] == "cid-123"
    assert kwargs["params"] == {"size": 3}


def test_4xx_raises_without_retry():
    get = AsyncMock(return_value=_resp(404, text="not found"))
    with pytest.raises(QuestionServiceError):
        _drive(get)
    assert get.await_count == 1  # no retry on client error


def test_5xx_retries_then_raises():
    get = AsyncMock(return_value=_resp(503))
    with pytest.raises(QuestionServiceError):
        _drive(get)
    assert get.await_count == 3  # 1 initial + 2 retries


def test_transport_error_then_success_recovers():
    get = AsyncMock(
        side_effect=[httpx.ConnectError("boom"), _resp(200, [{"id": "q1"}])]
    )
    out, _ = _drive(get)
    assert out == [{"id": "q1"}]
    assert get.await_count == 2


def test_transport_error_exhausts_and_raises():
    get = AsyncMock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(QuestionServiceError):
        _drive(get)
    assert get.await_count == 3
