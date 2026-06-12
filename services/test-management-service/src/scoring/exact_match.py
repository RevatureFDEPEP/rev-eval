from typing import Iterable

from .types import ScoreResult


def score_exact_match(correct_answers: Iterable, submitted_answers: Iterable) -> ScoreResult:
    """Score single-select / true-false questions.

    Full marks only when the submitted set equals the correct set; otherwise 0.
    """
    correct_set = set(correct_answers or [])
    submitted_set = set(submitted_answers or [])

    # A question with no defined correct answer can never be "correct" — never
    # award marks for an empty-vs-empty match.
    is_correct = bool(correct_set) and submitted_set == correct_set
    earned = 1.0 if is_correct else 0.0

    return ScoreResult(
        earned=earned,
        possible=1.0,
        is_correct=is_correct,
        details={
            "correct_count": len(correct_set),
            "submitted_count": len(submitted_set),
        },
    )
