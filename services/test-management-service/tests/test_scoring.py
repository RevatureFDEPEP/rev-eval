"""Unit tests for the pure scoring module — Feature 2."""
import pytest
from src.scoring import (
    ScoreResult,
    score_exact_match,
    score_partial_credit,
    score_question,
)

# ---------------------------------------------------------------------------
# Exact match (single-select / true-false)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "correct, submitted, expected_earned, expected_is_correct",
    [
        ([2], [2], 1.0, True),       # correct single-select
        ([2], [3], 0.0, False),      # wrong single-select
        ([2], [], 0.0, False),       # no answer
        ([2], [2, 3], 0.0, False),   # extra selection invalidates exact match
        ([True], [True], 1.0, True),   # true_false correct
        ([False], [True], 0.0, False),  # true_false wrong
    ],
)
def test_score_exact_match(correct, submitted, expected_earned, expected_is_correct):
    result = score_exact_match(correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.earned == expected_earned
    assert result.possible == 1.0
    assert result.is_correct is expected_is_correct


# ---------------------------------------------------------------------------
# Partial credit (multi-select)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "correct, submitted, expected_earned, expected_is_correct",
    [
        ([1, 2, 3], [1, 2, 3], 1.0, True),        # full match
        ([1, 2, 3], [1, 2], 2 / 3, False),         # 2 right, 0 wrong
        ([1, 2, 3], [1], 1 / 3, False),            # 1 right, 0 wrong
        ([1, 2, 3], [1, 2, 4], 1 / 3, False),      # 2 right, 1 wrong -> (2-1)/3
        ([1, 2], [1, 2, 3, 4], 0.0, False),        # 2 right, 2 wrong -> clamp 0
        ([1, 2, 3], [4, 5, 6], 0.0, False),        # all wrong -> clamp 0
        ([1, 2, 3], [], 0.0, False),               # empty -> 0
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


def test_partial_credit_no_correct_answers_defined():
    result = score_partial_credit([], [1])
    assert result.earned == 0.0
    assert result.is_correct is False


@pytest.mark.parametrize("correct, submitted", [([], []), (None, []), (None, None)])
def test_exact_match_empty_correct_never_awards_marks(correct, submitted):
    """S1: empty-vs-empty must not score full marks."""
    result = score_exact_match(correct, submitted)
    assert result.earned == 0.0
    assert result.is_correct is False


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_score_question_dispatches_mcq_to_exact():
    assert score_question("mcq", [2], [2]).is_correct is True
    assert score_question("mcq", [2], [3]).earned == 0.0


def test_score_question_dispatches_true_false_to_exact():
    assert score_question("true_false", [True], [True]).is_correct is True


def test_score_question_dispatches_multi_to_partial():
    result = score_question("multi", [1, 2, 3], [1, 2])
    assert result.earned == pytest.approx(2 / 3)
    assert result.is_correct is False


def test_score_question_is_case_insensitive_on_type():
    assert score_question("MCQ", [1], [1]).is_correct is True


def test_score_question_text_is_not_auto_scored():
    result = score_question("text", None, ["anything"])
    assert result.possible == 0.0
    assert result.is_correct is False


def test_score_question_unknown_type_raises():
    with pytest.raises(ValueError):
        score_question("essay", [1], [1])
