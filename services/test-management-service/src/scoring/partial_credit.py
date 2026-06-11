# src/scoring/partial_credit.py
"""Partial-credit scoring for multi-select questions via the Jaccard index.

MULTI questions earn ``|correct ∩ submitted| / |correct ∪ submitted|`` — a
submission that picks some-but-not-all correct options, or includes a wrong
one, lands between 0 and 1. Single-select questions (MCQ, TRUE_FALSE) have no
meaningful partial state, so they delegate to exact-match (binary 0/1)."""
from collections.abc import Iterable

from src.scoring import exact_match
from src.scoring.result import ScoreResult


def score_question(
    question_type: str,
    correct_answers: Iterable | None,
    submitted_answers: Iterable | None,
) -> ScoreResult:
    """Score one answer with partial credit. Pure: no I/O, no mutation.

    Raises ``ValueError`` for types this engine cannot auto-score (TEXT etc.).
    """
    qtype = (question_type or "").lower()

    if qtype != "multi":
        # Single-select / TRUE_FALSE: partial credit is undefined → exact match.
        return exact_match.score_question(question_type, correct_answers, submitted_answers)

    correct = exact_match._to_set(correct_answers)
    submitted = exact_match._to_set(submitted_answers)

    union = correct | submitted
    if not union:
        # No correct key AND no submission: vacuously perfect.
        return ScoreResult(is_correct=True, score=1.0, algorithm="partial_credit")

    jaccard = len(correct & submitted) / len(union)
    return ScoreResult(
        is_correct=correct == submitted,
        score=jaccard,
        max_score=1.0,
        algorithm="partial_credit",
    )
