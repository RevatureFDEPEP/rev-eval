"""
tests/test_quiz_session_scoring.py

Parametrized unit tests for pure scoring functions in quiz_session_service.
No DB, no HTTP -- only imports the pure functions from src.services.quiz_session_service.
"""
import os

# Set env vars BEFORE any src.* import so pydantic Settings does not blow up.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_mgmt.db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("ALLOW_ORIGINS", "*")
os.environ.setdefault("SERVICE_NAME", "test-management-service")
os.environ.setdefault("PORT", "8001")
os.environ.setdefault("SERVICE_HOSTNAME", "test-management-service")

import pytest
from src.services.quiz_session_service import (
    score_exact_match,
    score_jaccard,
    score_question,
    score_part,
)


# ---------------------------------------------------------------------------
# score_exact_match
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "selected, correct, expected",
    [
        # Exact match
        ([1], 1, 1.0),
        ([2], 2, 1.0),
        ([0], 0, 1.0),
        # Wrong answer
        ([2], 1, 0.0),
        ([0], 3, 0.0),
        # Empty selection
        ([], 1, 0.0),
        # Multiple selected (MCQ expects exactly one)
        ([1, 2], 1, 0.0),
        ([1, 2, 3], 1, 0.0),
        # True/False style (1 = True)
        ([1], 1, 1.0),
        ([0], 1, 0.0),
    ],
)
def test_score_exact_match(selected, correct, expected):
    assert score_exact_match(selected, correct) == expected


# ---------------------------------------------------------------------------
# score_jaccard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "selected, correct, expected",
    [
        # Perfect match
        ([1, 2, 3], [1, 2, 3], 1.0),
        ([1], [1], 1.0),
        # Partial: selected subset of correct
        ([1, 2], [1, 2, 3], pytest.approx(2 / 3)),
        # Partial: correct is subset of selected (over-selection)
        ([1, 2, 4], [1, 2, 3], pytest.approx(2 / 4)),  # union=4 items
        # All wrong
        ([4, 5], [1, 2, 3], 0.0),
        # Empty selected
        ([], [1, 2], 0.0),
        # Empty correct, empty selected -> full credit
        ([], [], 1.0),
        # Empty correct, non-empty selected -> zero credit
        ([1], [], 0.0),
        # Single correct, correct answer
        ([3], [3], 1.0),
        # Single correct, wrong answer
        ([2], [3], 0.0),
    ],
)
def test_score_jaccard(selected, correct, expected):
    assert score_jaccard(selected, correct) == expected


# ---------------------------------------------------------------------------
# score_question
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "question_type, selected, correct_answer, correct_answers, expected",
    [
        # MCQ: exact match
        ("mcq", [2], 2, None, 1.0),
        ("mcq", [1], 2, None, 0.0),
        ("mcq", [], 2, None, 0.0),
        ("mcq", [1, 2], 1, None, 0.0),
        # MCQ: no correct_answer stored -> 0
        ("mcq", [1], None, None, 0.0),
        # True/False: exact match
        ("true_false", [1], 1, None, 1.0),
        ("true_false", [0], 1, None, 0.0),
        ("true_false", [], 0, None, 0.0),
        # Multi: Jaccard
        ("multi", [1, 2, 3], None, [1, 2, 3], 1.0),
        ("multi", [1, 2], None, [1, 2, 3], pytest.approx(2 / 3)),
        ("multi", [], None, [1, 2], 0.0),
        ("multi", [], None, [], 1.0),
        # Unknown type -> 0
        ("text", [1], 1, None, 0.0),
        ("unknown", [1], 1, [1], 0.0),
    ],
)
def test_score_question(question_type, selected, correct_answer, correct_answers, expected):
    result = score_question(question_type, selected, correct_answer, correct_answers)
    assert result == expected


# ---------------------------------------------------------------------------
# score_part
# ---------------------------------------------------------------------------

def _make_questions(*specs):
    """
    Build a list of stored question dicts from (question_id, type, correct_answer, correct_answers) tuples.
    """
    questions = []
    for q_id, q_type, ca, cas in specs:
        questions.append({
            "question_id": q_id,
            "question_type": q_type,
            "correct_answer": ca,
            "correct_answers": cas,
        })
    return questions


def _make_answers(*specs):
    """Build answer list from (question_id, selected_answers) tuples."""
    return [{"question_id": q_id, "selected_answers": sel} for q_id, sel in specs]


@pytest.mark.parametrize(
    "stored_questions, answers, expected_count, expected_pct",
    [
        # All correct (3 MCQ)
        (
            _make_questions(("q1", "mcq", 1, None), ("q2", "mcq", 2, None), ("q3", "mcq", 3, None)),
            _make_answers(("q1", [1]), ("q2", [2]), ("q3", [3])),
            3.0,
            100.0,
        ),
        # None correct
        (
            _make_questions(("q1", "mcq", 1, None), ("q2", "mcq", 2, None)),
            _make_answers(("q1", [2]), ("q2", [1])),
            0.0,
            0.0,
        ),
        # Mixed: 2 correct out of 3
        (
            _make_questions(
                ("q1", "mcq", 1, None),
                ("q2", "mcq", 2, None),
                ("q3", "true_false", 0, None),
            ),
            _make_answers(("q1", [1]), ("q2", [9]), ("q3", [0])),
            2.0,
            pytest.approx(66.67),
        ),
        # Unanswered questions count as 0
        (
            _make_questions(("q1", "mcq", 1, None), ("q2", "mcq", 2, None)),
            _make_answers(("q1", [1])),  # q2 not answered
            1.0,
            50.0,
        ),
        # Partial credit (multi-select Jaccard)
        (
            _make_questions(("q1", "multi", None, [1, 2, 3])),
            _make_answers(("q1", [1, 2])),
            pytest.approx(2 / 3),
            pytest.approx(round(2 / 3 / 1 * 100, 2)),
        ),
        # Empty question list -> 0%
        (
            [],
            [],
            0.0,
            0.0,
        ),
        # Single question, correct
        (
            _make_questions(("q1", "true_false", 1, None)),
            _make_answers(("q1", [1])),
            1.0,
            100.0,
        ),
        # All answers empty (fully unanswered)
        (
            _make_questions(("q1", "mcq", 1, None), ("q2", "mcq", 2, None)),
            [],
            0.0,
            0.0,
        ),
    ],
)
def test_score_part(stored_questions, answers, expected_count, expected_pct):
    count, pct = score_part(stored_questions, answers)
    assert count == expected_count
    assert pct == expected_pct
