"""Exact-match scoring for MCQ and TRUE_FALSE questions."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.scoring import ScoreResult


def score_question(
    question_type: str,
    correct_answers: list[Any] | None,
    submitted_answers: list[Any],
) -> "ScoreResult":
    """Score a single-answer question (mcq / true_false).

    question_type is part of the shared scorer contract and lets this function
    branch per type (e.g. true_false-specific normalization) as the taxonomy
    grows; today mcq and true_false share the same set-equality rule.
    """
    from src.scoring import ScoreResult

    if correct_answers is None:
        return ScoreResult(is_correct=False, points_earned=0.0)

    hit = set(map(str, submitted_answers)) == set(map(str, correct_answers))
    return ScoreResult(is_correct=hit, points_earned=1.0 if hit else 0.0)
