import pytest

from src.scoring import ScoreResult
from src.scoring import exact_match, partial_credit


# ---------------------------------------------------------------------------
# ScoreResult dataclass
# ---------------------------------------------------------------------------

def test_score_result_is_immutable():
    r = ScoreResult(earned=1.0, max_points=1.0, is_correct=True)
    with pytest.raises(Exception):
        r.earned = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exact-match (single-select)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "correct, submitted, expected_earned, expected_correct",
    [
        # correct answer selected
        (["A"], ["A"], 1.0, True),
        # wrong answer selected
        (["A"], ["B"], 0.0, False),
        # nothing submitted
        (["A"], [], 0.0, False),
    ],
)
def test_exact_match(correct, submitted, expected_earned, expected_correct):
    result = exact_match.score_question("SINGLE_SELECT", correct, submitted)
    assert result.earned == expected_earned
    assert result.is_correct == expected_correct
    assert result.max_points == 1.0


def test_exact_match_respects_max_points():
    result = exact_match.score_question("SINGLE_SELECT", ["A"], ["A"], max_points=2.0)
    assert result.earned == 2.0
    assert result.max_points == 2.0


# ---------------------------------------------------------------------------
# Full-match (multi-select, all correct, zero false positives)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "correct, submitted",
    [
        (["A", "B"], ["A", "B"]),
        (["A", "B"], ["B", "A"]),  # order-independent
        (["A", "B", "C"], ["A", "B", "C"]),
    ],
)
def test_full_match(correct, submitted):
    result = partial_credit.score_question("MULTI_SELECT", correct, submitted)
    assert result.earned == 1.0
    assert result.is_correct is True


# ---------------------------------------------------------------------------
# Partial-credit (multi-select, some hits, zero false positives)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "correct, submitted, expected_earned",
    [
        # 1/2 correct, 0 FP → 0.5
        (["A", "B"], ["A"], 0.5),
        # 2/3 correct, 0 FP → 0.6667
        (["A", "B", "C"], ["A", "B"], round(2 / 3, 4)),
        # nothing submitted → 0
        (["A", "B"], [], 0.0),
    ],
)
def test_partial_credit_no_false_positives(correct, submitted, expected_earned):
    result = partial_credit.score_question("MULTI_SELECT", correct, submitted)
    assert result.earned == pytest.approx(expected_earned, abs=1e-4)
    assert result.is_correct is False


# ---------------------------------------------------------------------------
# Jaccard / penalty (multi-select, false positives reduce or zero the score)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "correct, submitted, expected_earned",
    [
        # 2/3 correct + 1 FP → max(0, 2-1)/3 = 1/3
        (["A", "B", "C"], ["A", "B", "D"], round(1 / 3, 4)),
        # 1/2 correct + 1 FP → max(0, 0)/2 = 0
        (["A", "B"], ["A", "C"], 0.0),
        # 0 correct, all FP
        (["A", "B"], ["C", "D"], 0.0),
        # 1 correct + 1 FP over-selected → max(0, 0)/1 = 0
        (["A"], ["A", "B"], 0.0),
    ],
)
def test_jaccard_penalty(correct, submitted, expected_earned):
    result = partial_credit.score_question("MULTI_SELECT", correct, submitted)
    assert result.earned == pytest.approx(expected_earned, abs=1e-4)
    assert result.is_correct is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_partial_credit_empty_correct_answers():
    result = partial_credit.score_question("MULTI_SELECT", [], ["A"])
    assert result.earned == 0.0
    assert result.is_correct is False


def test_exact_match_question_type_param_is_accepted():
    # question_type is part of the interface but does not change behaviour
    result = exact_match.score_question("SINGLE_SELECT", ["X"], ["X"])
    assert result.is_correct is True
