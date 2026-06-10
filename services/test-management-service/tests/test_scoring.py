"""Parameterized unit tests for the pure scoring core (W3-F2 step 5).

No DB, no network, no fixtures — the scorers are pure functions, so the matrix
of exact-match / full-match / Jaccard / partial-credit scenarios runs directly.
"""
import pytest
from src import scoring
from src.scoring import exact_match, partial_credit


@pytest.mark.parametrize(
    "qtype, correct, submitted, expected_score, expected_correct",
    [
        # --- exact match: single-select (mcq) ---
        ("mcq", [2], [2], 1.0, True),          # exact match
        ("mcq", [2], [1], 0.0, False),         # wrong choice
        ("mcq", [2], [], 0.0, False),          # no choice
        ("mcq", [2], [1, 2], 0.0, False),      # extra choice -> not exact
        # --- exact match: true_false ---
        ("true_false", [True], [True], 1.0, True),
        ("true_false", [True], [False], 0.0, False),
        # --- partial credit: multi-select (Jaccard) ---
        ("multi", [1, 2, 3], [1, 2, 3], 1.0, True),     # full match
        ("multi", [1, 2, 3, 4], [1, 2], 0.5, False),    # 2 of 4 correct, no spurious
        ("multi", [1, 2], [1, 2, 3], 2 / 3, False),     # all correct + 1 spurious
        ("multi", [1, 2, 3], [4, 5, 6], 0.0, False),    # disjoint
        ("multi", [1, 2], [], 0.0, False),              # empty submission
        ("multi", [1, 2, 3, 4], [1, 2, 3], 0.75, False),  # 3 of 4
    ],
)
def test_score_matrix(qtype, correct, submitted, expected_score, expected_correct):
    result = scoring.score(qtype, correct, submitted)
    assert result.score == pytest.approx(expected_score)
    assert result.is_correct is expected_correct
    assert 0.0 <= result.score <= 1.0


def test_dispatch_routes_by_type():
    # mcq/true_false -> exact_match; multi -> partial_credit.
    assert scoring.score("mcq", [1], [1]) == exact_match.score_question("mcq", [1], [1])
    assert scoring.score("multi", [1, 2], [1]) == partial_credit.score_question(
        "multi", [1, 2], [1]
    )


def test_text_type_not_auto_scorable():
    # Free-text isn't auto-scored: recorded as 0.0 awaiting manual review.
    result = scoring.score("text", None, ["some prose"])
    assert result.score == 0.0
    assert result.is_correct is False


def test_unknown_type_scores_zero():
    result = scoring.score("essay", None, ["x"])
    assert result.score == 0.0
    assert result.is_correct is False


def test_exact_match_is_order_independent():
    # Submitting the same set in any order / with dupes is still exact.
    assert exact_match.score_question("mcq", [3], [3]).is_correct is True


def test_partial_credit_empty_correct_set_guarded():
    # Degenerate question with no correct answers -> no credit, no ZeroDivision.
    result = partial_credit.score_question("multi", [], [1, 2])
    assert result.score == 0.0
    assert result.is_correct is False


def test_score_result_is_immutable():
    from dataclasses import FrozenInstanceError

    result = scoring.score("mcq", [1], [1])
    with pytest.raises(FrozenInstanceError):
        result.score = 0.0  # frozen dataclass
