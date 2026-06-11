from typing import Iterable

from .types import ScoreResult


def score_partial_credit(correct_answers: Iterable, submitted_answers: Iterable) -> ScoreResult:
    """Score multi-select questions with set-overlap partial credit.

    earned = clamp((true_positives - false_positives) / |correct|, 0, 1)

    A wrong selection cancels a right one, so guessing everything scores 0
    (false positives equal the count of correct answers). is_correct is True
    only on an exact set match.
    """
    correct_set = set(correct_answers or [])
    submitted_set = set(submitted_answers or [])

    if not correct_set:
        return ScoreResult(
            earned=0.0,
            possible=1.0,
            is_correct=False,
            details={"reason": "no correct answers defined"},
        )

    true_positives = len(correct_set & submitted_set)
    false_positives = len(submitted_set - correct_set)
    false_negatives = len(correct_set - submitted_set)

    raw = (true_positives - false_positives) / len(correct_set)
    earned = max(0.0, min(1.0, raw))
    is_correct = submitted_set == correct_set

    return ScoreResult(
        earned=earned,
        possible=1.0,
        is_correct=is_correct,
        details={
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
    )
