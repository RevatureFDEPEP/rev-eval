"""Unit tests for the quiz-session pure helpers (W3-F1, Part B).

SYNC only — imports *only* ``src.services.quiz_session_helpers`` (which in turn
pulls only the pure schema module), so no DB/httpx/Mongo and no route/model/app
enters the coverage denominator. Covers the qms-sample query builder (n/skills),
duration/expiry math, token minting, and the sampled-dict -> QuizQuestionOut
mapping (answer-key never carried).
"""

import re
from datetime import datetime, timedelta

from src.schemas.quiz_session_schema import QuizQuestionOut
from src.services.quiz_session_helpers import (
    DEFAULT_DURATION_SECONDS,
    MAX_SAMPLE_QUERY_SIZE,
    build_sample_query,
    compute_expires_at,
    map_sample_to_question,
    mint_session_token,
    resolve_duration_seconds,
)

# ---------------------------------------------------------------------------
# build_sample_query
# ---------------------------------------------------------------------------


def test_query_defaults_n_to_20_when_none():
    assert build_sample_query(None, None) == {"n": 20}


def test_query_defaults_n_to_20_when_nonpositive():
    assert build_sample_query(0, None) == {"n": 20}
    assert build_sample_query(-5, None) == {"n": 20}


def test_query_uses_test_question_count():
    assert build_sample_query(15, None) == {"n": 15}


def test_query_caps_n_to_qms_public_maximum():
    assert build_sample_query(MAX_SAMPLE_QUERY_SIZE + 1, None) == {
        "n": MAX_SAMPLE_QUERY_SIZE
    }
    assert build_sample_query(10_000, None) == {"n": MAX_SAMPLE_QUERY_SIZE}


def test_query_joins_skills_csv():
    assert build_sample_query(10, ["python", "sql"]) == {
        "n": 10,
        "skills": "python,sql",
    }


def test_query_strips_and_drops_blank_skills():
    assert build_sample_query(10, ["python", " ", "", "sql "]) == {
        "n": 10,
        "skills": "python,sql",
    }


def test_query_omits_skills_when_all_blank():
    assert build_sample_query(10, [" ", ""]) == {"n": 10}


def test_query_omits_skills_when_empty_list():
    assert build_sample_query(10, []) == {"n": 10}


# ---------------------------------------------------------------------------
# resolve_duration_seconds
# ---------------------------------------------------------------------------


def test_duration_from_timedelta():
    assert resolve_duration_seconds(timedelta(minutes=30)) == 1800


def test_duration_from_int():
    assert resolve_duration_seconds(900) == 900


def test_duration_from_float():
    assert resolve_duration_seconds(120.0) == 120


def test_duration_none_defaults():
    assert resolve_duration_seconds(None) == DEFAULT_DURATION_SECONDS


def test_duration_nonpositive_defaults():
    assert resolve_duration_seconds(timedelta(seconds=0)) == DEFAULT_DURATION_SECONDS
    assert resolve_duration_seconds(-10) == DEFAULT_DURATION_SECONDS


# ---------------------------------------------------------------------------
# compute_expires_at
# ---------------------------------------------------------------------------


def test_compute_expires_at_adds_seconds():
    now = datetime(2026, 6, 17, 12, 0, 0)
    assert compute_expires_at(now, 3600) == datetime(2026, 6, 17, 13, 0, 0)


def test_compute_expires_at_is_after_server_now():
    now = datetime(2026, 6, 17, 12, 0, 0)
    assert compute_expires_at(now, 1) > now


# ---------------------------------------------------------------------------
# mint_session_token
# ---------------------------------------------------------------------------


def test_token_is_64_hex_chars():
    token = mint_session_token()
    assert len(token) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", token)


def test_tokens_are_unique():
    assert mint_session_token() != mint_session_token()


# ---------------------------------------------------------------------------
# map_sample_to_question
# ---------------------------------------------------------------------------


def test_map_sample_remaps_qms_fields():
    doc = {
        "_id": "abc123",
        "question_text": "What is 2+2?",
        "type": "mcq",
        "difficulty": "easy",
        "options": [{"option_id": 1, "text": "4"}],
    }
    q = map_sample_to_question(doc)
    assert isinstance(q, QuizQuestionOut)
    assert q.question_id == "abc123"
    assert q.question_type == "mcq"
    assert q.options == [{"option_id": 1, "text": "4"}]


def test_map_sample_never_carries_answer_fields():
    doc = {
        "_id": "x",
        "question_text": "q",
        "type": "multi",
        "difficulty": "hard",
        "options": [{"option_id": 1, "text": "a"}],
        "correct_answers": [1],
        "sample_answer": "secret",
    }
    q = map_sample_to_question(doc)
    dumped = q.model_dump()
    assert "correct_answers" not in dumped
    assert "sample_answer" not in dumped


def test_map_sample_stringifies_id():
    q = map_sample_to_question({"_id": 999, "question_text": "q", "type": "mcq"})
    assert q.question_id == "999"


def test_map_sample_accepts_already_mapped_field_names():
    doc = {"question_id": "q9", "question_type": "text", "question_text": "essay?"}
    q = map_sample_to_question(doc)
    assert q.question_id == "q9"
    assert q.question_type == "text"


def test_map_sample_defaults_missing_difficulty_and_text():
    q = map_sample_to_question({"_id": "1"})
    assert q.difficulty == "medium"
    assert q.question_text == ""
    assert q.question_type == ""
    assert q.options is None
