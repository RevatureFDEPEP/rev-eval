"""Exact-match scoring for MCQ and TRUE_FALSE questions."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.scoring import ScoreResult


def score_question(
    correct_answers: list[Any] | None,
    submitted_answers: list[Any],
) -> "ScoreResult":
    from src.scoring import ScoreResult

    if not correct_answers or not submitted_answers:
        return ScoreResult(is_correct=False, points_earned=0.0)

    hit = set(map(str, submitted_answers)) == set(map(str, correct_answers))
    return ScoreResult(is_correct=hit, points_earned=1.0 if hit else 0.0)
