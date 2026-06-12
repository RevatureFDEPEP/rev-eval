"""Unit tests for the pure scoring engine (W3-F2).

No DB, no I/O — exercises exact-match and partial-credit (Jaccard) across a
matrix of question types and correct/submitted combinations.
"""
import pytest

from src.scoring import exact_match, partial_credit


# --- exact_match -----------------------------------------------------------

@pytest.mark.parametrize(
    "qtype, correct, submitted, expected_correct, expected_score",
    [
        # MCQ single-select
        ("mcq", [2], [2], True, 1.0),
        ("mcq", [2], [1], False, 0.0),
        ("mcq", [2], [], False, 0.0),
        # MULTI: order-insensitive, all-or-nothing
        ("multi", [1, 3], [3, 1], True, 1.0),
        ("multi", [1, 3], [1, 3, 2], False, 0.0),  # superset
        ("multi", [1, 3], [1], False, 0.0),         # subset
        ("multi", [1, 3], [2, 4], False, 0.0),      # disjoint
        # MULTI duplicates collapse
        ("multi", [1, 2], [1, 2, 2], True, 1.0),
        # TRUE_FALSE
        ("true_false", [True], [True], True, 1.0),
        ("true_false", [True], [False], False, 0.0),
        # Case-insensitive question type
        ("MCQ", [2], [2], True, 1.0),
    ],
)
def test_exact_match(qtype, correct, submitted, expected_correct, expected_score):
    result = exact_match.score_question(qtype, correct, submitted)
    assert result.is_correct is expected_correct
    assert result.score == pytest.approx(expected_score)
    assert result.max_score == 1.0
    assert result.algorithm == "exact_match"


@pytest.mark.parametrize("qtype", ["text", "unknown", "", None])
def test_exact_match_rejects_unscorable_types(qtype):
    with pytest.raises(ValueError):
        exact_match.score_question(qtype, [1], [1])


def test_exact_match_none_answers_score_zero():
    result = exact_match.score_question("mcq", [2], None)
    assert result.is_correct is False
    assert result.score == 0.0


# --- partial_credit (Jaccard) ---------------------------------------------

@pytest.mark.parametrize(
    "correct, submitted, expected_score, expected_correct",
    [
        ([1, 2, 3], [1, 2, 3], 1.0, True),       # full match
        ([1, 2, 3], [1, 2], 2 / 3, False),       # missing one
        ([1, 2, 3], [1, 2, 3, 4], 3 / 4, False), # one extra
        ([1, 2, 3], [1, 4], 1 / 4, False),       # one right, one wrong
        ([1, 2, 3], [4, 5], 0.0, False),         # disjoint
        ([1, 2, 3], [], 0.0, False),             # nothing submitted
        ([1, 2], [1, 2, 2], 1.0, True),          # duplicate collapses
    ],
)
def test_partial_credit_multi(correct, submitted, expected_score, expected_correct):
    result = partial_credit.score_question("multi", correct, submitted)
    assert result.score == pytest.approx(expected_score)
    assert result.is_correct is expected_correct
    assert result.algorithm == "partial_credit"


def test_partial_credit_empty_union_is_vacuously_correct():
    # No correct key AND no submission -> Jaccard of two empty sets.
    result = partial_credit.score_question("multi", [], [])
    assert result.is_correct is True
    assert result.score == 1.0


@pytest.mark.parametrize(
    "qtype, correct, submitted, expected_score",
    [
        ("mcq", [2], [2], 1.0),
        ("mcq", [2], [1], 0.0),
        ("true_false", [False], [False], 1.0),
    ],
)
def test_partial_credit_single_select_delegates_to_exact(qtype, correct, submitted, expected_score):
    # Single-select has no partial state: binary, via exact-match.
    result = partial_credit.score_question(qtype, correct, submitted)
    assert result.score == pytest.approx(expected_score)
    assert result.algorithm == "exact_match"


def test_partial_credit_rejects_text():
    with pytest.raises(ValueError):
        partial_credit.score_question("text", None, ["anything"])
