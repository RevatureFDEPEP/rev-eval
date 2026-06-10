from dataclasses import dataclass, field
from typing import Any

from src.scoring import exact_match, partial_credit


@dataclass
class ScoreResult:
    is_correct: bool
    points_earned: float
    max_points: float = field(default=1.0)
    requires_manual_review: bool = field(default=False)


def score(
    question_type: str,
    correct_answers: list[Any] | None,
    submitted_answers: list[Any],
) -> ScoreResult:
    """Dispatch to the appropriate scoring algorithm by question type."""
    if question_type in ("mcq", "true_false"):
        return exact_match.score_question(correct_answers, submitted_answers)
    return partial_credit.score_question(
        question_type, correct_answers, submitted_answers
    )
