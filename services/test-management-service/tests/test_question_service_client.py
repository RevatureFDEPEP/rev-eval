"""
tests/test_question_service_client.py

question-management-service returns answer keys only to trainers and to this
service (identified by its internal token). These tests cover this side of that
contract: the token goes to question-management and nowhere else, scoring works
from the keys it returns, participants never see them, and a response without
keys fails closed instead of scoring every answer as wrong.
"""
import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mgmt.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from src.config.settings import settings  # noqa: E402
from src.services.quiz_session_service import (  # noqa: E402
    _normalize_question,
    _safe_question_out,
    fetch_questions_for_part,
    grade_part,
    question_service_headers,
)
from src.utils.dependencies import user_service_headers  # noqa: E402

QS_URL = "http://question-management-service:8003"
TOKEN = "internal-test-token"

# What question-management returns to an internal caller: answer keys included.
_WITH_KEYS = [
    {"_id": "q1", "type": "mcq", "difficulty": "easy", "question_text": "2 + 2?",
     "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}], "correct_answers": [2]},
    {"_id": "q2", "type": "true_false", "difficulty": "easy", "question_text": "Python is typed?",
     "options": None, "correct_answers": [True]},
    {"_id": "q3", "type": "multi", "difficulty": "easy", "question_text": "Even numbers?",
     "options": [{"option_id": 1, "text": "2"}, {"option_id": 2, "text": "3"}, {"option_id": 3, "text": "4"}],
     "correct_answers": [1, 3]},
]


class _Resp:
    def __init__(self, data):
        self.status_code = 200
        self._data = data
        self.text = ""

    def json(self):
        return self._data


def _recording_client(data):
    seen = []

    class _Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, headers=None, **k):
            seen.append((url, dict(headers or {})))
            return _Resp(data)

    return _Client, seen


def _fetch(data, token=TOKEN):
    client, seen = _recording_client(data)
    with patch.object(settings, "INTERNAL_SERVICE_TOKEN", token), patch("httpx.AsyncClient", client):
        questions = asyncio.run(fetch_questions_for_part(QS_URL, 1, {"easy": 3}, []))
    return questions, seen


class TestInternalTokenToQuestionService:
    def test_fetch_sends_internal_token_to_question_service(self):
        _, seen = _fetch(_WITH_KEYS)
        assert len(seen) == 1
        url, headers = seen[0]
        assert url.startswith(f"{QS_URL}/v1/api/questions/")
        assert headers == {"X-Internal-Service-Token": TOKEN}

    def test_no_internal_header_when_token_not_configured(self):
        with patch.object(settings, "INTERNAL_SERVICE_TOKEN", None):
            assert question_service_headers() == {}

    def test_internal_token_is_never_sent_to_user_service(self):
        with patch.object(settings, "INTERNAL_SERVICE_TOKEN", TOKEN):
            headers = user_service_headers("Bearer participant-jwt")
        assert headers == {"Authorization": "Bearer participant-jwt"}
        assert "X-Internal-Service-Token" not in headers


class TestScoringWithAnswerKeys:
    def test_scores_from_returned_keys_and_hides_them_from_participants(self):
        raw, _ = _fetch(_WITH_KEYS)
        stored = [_normalize_question(q) for q in raw]

        all_right = [
            {"question_id": "q1", "selected_answers": [2]},
            {"question_id": "q2", "selected_answers": [True]},
            {"question_id": "q3", "selected_answers": [1, 3]},
        ]
        assert grade_part([dict(q) for q in stored], all_right) == (3.0, 100.0)

        all_wrong = [
            {"question_id": "q1", "selected_answers": [1]},
            {"question_id": "q2", "selected_answers": [False]},
            {"question_id": "q3", "selected_answers": [2]},
        ]
        assert grade_part([dict(q) for q in stored], all_wrong) == (0.0, 0.0)

        for q in stored:
            shown = _safe_question_out(q).model_dump()
            assert "correct_answer" not in shown and "correct_answers" not in shown

    def test_response_without_answer_keys_fails_closed(self):
        # What question-management returns to a caller it does not trust with keys.
        without_keys = [
            {k: v for k, v in q.items() if k != "correct_answers"} for q in _WITH_KEYS
        ]
        with pytest.raises(HTTPException) as exc:
            _fetch(without_keys)
        assert exc.value.status_code == 503
