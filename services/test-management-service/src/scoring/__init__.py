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
    """Dispatch to the appropriate scoring algorithm by question type.

    Unknown or human-graded types (text, or any type we don't auto-score) fall
    through to manual review rather than being silently set-scored.
    """
    if question_type in ("mcq", "true_false"):
        return exact_match.score_question(
            question_type, correct_answers, submitted_answers
        )
    if question_type == "multi":
        return partial_credit.score_question(
            question_type, correct_answers, submitted_answers
        )
    # text and any unrecognized type cannot be auto-scored.
    return ScoreResult(is_correct=False, points_earned=0.0, requires_manual_review=True)
