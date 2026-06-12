"""Unit tests for the pure scoring module."""
import pytest
from src.scoring import (
    ScoreResult,
    score_exact_match,
    score_partial_credit,
    score_question,
)

# --- Exact match (single-select / true-false) -----------------------------


@pytest.mark.parametrize(
    "correct, submitted, expected_earned, expected_is_correct",
    [
        ([2], [2], 1.0, True),
        ([2], [3], 0.0, False),
        ([2], [], 0.0, False),
        ([2], [2, 3], 0.0, False),  # extra selection invalidates exact match
        ([True], [True], 1.0, True),
        ([False], [True], 0.0, False),
    ],
)
def test_score_exact_match(correct, submitted, expected_earned, expected_is_correct):
    result = score_exact_match(correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.earned == expected_earned
    assert result.possible == 1.0
    assert result.is_correct is expected_is_correct


@pytest.mark.parametrize("correct, submitted", [([], []), (None, []), (None, None)])
def test_exact_match_empty_correct_never_awards_marks(correct, submitted):
    result = score_exact_match(correct, submitted)
    assert result.earned == 0.0
    assert result.is_correct is False


# --- Partial credit (multi-select) -----------------------------------------


@pytest.mark.parametrize(
    "correct, submitted, expected_earned, expected_is_correct",
    [
        ([1, 2, 3], [1, 2, 3], 1.0, True),
        ([1, 2, 3], [1, 2], 2 / 3, False),
        ([1, 2, 3], [1], 1 / 3, False),
        ([1, 2, 3], [1, 2, 4], 1 / 3, False),  # 2 right, 1 wrong -> (2-1)/3
        ([1, 2], [1, 2, 3, 4], 0.0, False),  # 2 right, 2 wrong -> clamp 0
        ([1, 2, 3], [4, 5, 6], 0.0, False),
        ([1, 2, 3], [], 0.0, False),
    ],
)
def test_score_partial_credit(correct, submitted, expected_earned, expected_is_correct):
    result = score_partial_credit(correct, submitted)
    assert result.earned == pytest.approx(expected_earned)
    assert result.possible == 1.0
    assert result.is_correct is expected_is_correct


def test_partial_credit_records_audit_counts():
    result = score_partial_credit([1, 2, 3], [1, 2, 4])
    assert result.details["true_positives"] == 2
    assert result.details["false_positives"] == 1
    assert result.details["false_negatives"] == 1


# --- Dispatch ---------------------------------------------------------------


def test_score_question_dispatch():
    assert score_question("mcq", [2], [2]).is_correct is True
    assert score_question("true_false", [True], [True]).is_correct is True
    assert score_question("multi", [1, 2, 3], [1, 2]).earned == pytest.approx(2 / 3)


def test_score_question_is_case_insensitive_on_type():
    assert score_question("MCQ", [1], [1]).is_correct is True


def test_score_question_text_is_not_auto_scored():
    result = score_question("text", None, ["anything"])
    assert result.possible == 0.0
    assert result.is_correct is False


def test_score_question_unknown_type_raises():
    with pytest.raises(ValueError):
        score_question("essay", [1], [1])
