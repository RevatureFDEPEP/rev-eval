"""Pure unit tests for the scoring module — no DB, no HTTP."""

import pytest

from src.scoring import ScoreResult, score


@pytest.mark.parametrize(
    "question_type,correct,submitted,expected_points,expected_correct",
    [
        # MCQ
        ("mcq", [1], [1], 1.0, True),
        ("mcq", [1], [2], 0.0, False),
        ("mcq", [0], [], 0.0, False),
        # TRUE_FALSE
        ("true_false", [True], [True], 1.0, True),
        ("true_false", [True], [False], 0.0, False),
        ("true_false", [False], [False], 1.0, True),
        # MULTI — full match
        ("multi", [0, 2], [0, 2], 1.0, True),
        ("multi", [0, 2], [2, 0], 1.0, True),  # order-independent
        # MULTI — partial credit (Jaccard)
        ("multi", [0, 1, 2], [0, 2], 2 / 3, False),
        ("multi", [0, 2], [0, 1, 2], 2 / 3, False),
        # MULTI — no overlap
        ("multi", [0, 2], [1], 0.0, False),
        ("multi", [0, 2], [], 0.0, False),
        # TEXT — always 0, manual review
        ("text", None, ["some answer"], 0.0, False),
        ("text", None, [], 0.0, False),
    ],
)
def test_score(question_type, correct, submitted, expected_points, expected_correct):
    result = score(question_type, correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.is_correct == expected_correct
    assert result.points_earned == pytest.approx(expected_points, abs=1e-3)
    assert result.max_points == 1.0


def test_text_requires_manual_review():
    result = score("text", None, ["anything"])
    assert result.requires_manual_review is True


def test_mcq_does_not_require_manual_review():
    result = score("mcq", [1], [1])
    assert result.requires_manual_review is False


def test_multi_does_not_require_manual_review():
    result = score("multi", [0, 1], [0, 1])
    assert result.requires_manual_review is False
