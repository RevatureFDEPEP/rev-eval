from collections.abc import Sequence

from src.scoring import ScoreResult


def score_question(
    question_type: str,
    correct_answers: Sequence[str],
    submitted_answers: Sequence[str],
    max_points: float = 1.0,
) -> ScoreResult:
    correct = set(correct_answers)
    submitted = set(submitted_answers)
    if not correct:
        return ScoreResult(earned=0.0, max_points=max_points, is_correct=False)
    hits = len(correct & submitted)
    false_positives = len(submitted - correct)
    ratio = max(0.0, hits - false_positives) / len(correct)
    earned = round(ratio * max_points, 4)
    return ScoreResult(earned=earned, max_points=max_points, is_correct=ratio == 1.0)
