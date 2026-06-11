"""Partial-credit scoring for MULTI questions (Jaccard similarity)."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.scoring import ScoreResult


def score_question(
    question_type: str,
    correct_answers: list[Any] | None,
    submitted_answers: list[Any],
) -> "ScoreResult":
    """Score a multi-select question with Jaccard partial credit.

    question_type is part of the shared scorer contract (mirrors exact_match);
    today only `multi` routes here, but the param keeps the door open for other
    set-overlap types without a signature change.
    """
    from src.scoring import ScoreResult

    # MULTI: Jaccard similarity between correct and submitted sets.
    correct = set(map(str, correct_answers or []))
    submitted = set(map(str, submitted_answers or []))

    union = correct | submitted
    if not union:
        return ScoreResult(is_correct=False, points_earned=0.0)

    jaccard = len(correct & submitted) / len(union)
    # Grading precision: partial credit is rounded to 4 decimal places. This is
    # the contract downstream reporting (W4-F1) should aggregate against — change
    # it deliberately, as it sets the floor for score reproducibility.
    return ScoreResult(
        is_correct=(jaccard == 1.0),
        points_earned=round(jaccard, 4),
    )
