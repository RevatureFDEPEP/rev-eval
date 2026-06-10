"""Partial-credit scoring for MULTI questions; no-op for TEXT."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.scoring import ScoreResult


def score_question(
    question_type: str,
    correct_answers: list[Any] | None,
    submitted_answers: list[Any],
) -> "ScoreResult":
    from src.scoring import ScoreResult

    if question_type == "text":
        return ScoreResult(
            is_correct=False, points_earned=0.0, requires_manual_review=True
        )

    # MULTI: Jaccard similarity between correct and submitted sets.
    correct = set(map(str, correct_answers or []))
    submitted = set(map(str, submitted_answers or []))

    union = correct | submitted
    if not union:
        return ScoreResult(is_correct=False, points_earned=0.0)

    jaccard = len(correct & submitted) / len(union)
    return ScoreResult(
        is_correct=(jaccard == 1.0),
        points_earned=round(jaccard, 4),
    )
