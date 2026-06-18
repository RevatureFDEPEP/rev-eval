"""
Partial-credit scoring using Jaccard similarity.

Jaccard(A, B) = |A ∩ B| / |A ∪ B|

- score == 1.0  → all correct answers selected and nothing extra (is_correct=True)
- 0 < score < 1 → partial credit (is_correct=False)
- score == 0.0  → no overlap at all (is_correct=False)

Applies to any question type; callers should prefer this scorer for
multi-select and free-text questions where partial credit is appropriate.

No database access or side effects.
"""
from typing import Any, List

from src.scoring.models import ScoreResult


def _normalise(answers: List[Any]) -> frozenset:
    return frozenset(str(a).strip().lower() for a in answers)


def score_question(
    question_type: str,
    correct_answers: List[Any],
    submitted_answers: List[Any],
) -> ScoreResult:
    """Return a ScoreResult using Jaccard-similarity partial-credit logic."""
    correct = _normalise(correct_answers)
    submitted = _normalise(submitted_answers)

    if not correct and not submitted:
        return ScoreResult(
            score=1.0,
            is_correct=True,
            points_earned=1.0,
            points_possible=1.0,
            details="both answer sets empty — full credit",
        )

    intersection = correct & submitted
    union = correct | submitted

    jaccard = len(intersection) / len(union) if union else 0.0
    is_correct = jaccard == 1.0

    correct_hits = len(intersection)
    total_correct = len(correct)
    extra_count = len(submitted - correct)

    details = (
        f"Jaccard {jaccard:.3f}: {correct_hits}/{total_correct} correct"
        + (f", {extra_count} extra" if extra_count else "")
    )

    return ScoreResult(
        score=jaccard,
        is_correct=is_correct,
        points_earned=jaccard,
        points_possible=1.0,
        details=details,
    )
