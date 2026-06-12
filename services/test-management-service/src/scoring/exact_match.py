# src/scoring/exact_match.py
"""Exact-match scoring: full credit only when the submitted answer set is
identical to the correct answer set, zero otherwise. Applies uniformly to
single-select (MCQ, TRUE_FALSE) and multi-select (MULTI) questions."""
from collections.abc import Iterable

from src.scoring.result import ScoreResult

# Question types this module knows how to score (lowercase, matching the
# values question-management-service stores via ``use_enum_values``).
_SCORABLE = {"mcq", "multi", "true_false"}


def _to_set(answers: Iterable | None) -> frozenset:
    """Order-insensitive, duplicate-collapsed view of an answer list.

    ``correct_answers``/``submitted_answers`` are 1-indexed option positions
    (int) for MCQ/MULTI or a single bool for TRUE_FALSE; a missing/None answer
    is treated as the empty set so an unanswered question scores zero.
    """
    if answers is None:
        return frozenset()
    return frozenset(answers)


def score_question(
    question_type: str,
    correct_answers: Iterable | None,
    submitted_answers: Iterable | None,
) -> ScoreResult:
    """Score one answer by exact set equality. Pure: no I/O, no mutation.

    Raises ``ValueError`` for types this engine cannot auto-score (e.g. TEXT,
    which is graded against a sample answer, not a key).
    """
    qtype = (question_type or "").lower()
    if qtype not in _SCORABLE:
        raise ValueError(f"exact_match cannot score question type {question_type!r}")

    correct = _to_set(correct_answers)
    submitted = _to_set(submitted_answers)
    is_correct = correct == submitted
    return ScoreResult(
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0,
        max_score=1.0,
        algorithm="exact_match",
    )
