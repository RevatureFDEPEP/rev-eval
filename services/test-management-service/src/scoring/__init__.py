from dataclasses import dataclass
from typing import Optional

from src.scoring.exact_match import score_exact
from src.scoring.partial_credit import score_jaccard


@dataclass
class ScoreResult:
    score: Optional[float]
    algorithm: str


def score_question(
    question_type: str,
    correct_answers: Optional[list],
    submitted_answers: list,
) -> ScoreResult:
    if not correct_answers:
        return ScoreResult(None, "none")

    qt = (question_type or "").lower()

    if qt in ("mcq", "true_false"):
        return ScoreResult(score_exact(correct_answers, submitted_answers), "exact_match")
    if qt == "multi":
        return ScoreResult(score_jaccard(correct_answers, submitted_answers), "jaccard")
    return ScoreResult(None, "none")
