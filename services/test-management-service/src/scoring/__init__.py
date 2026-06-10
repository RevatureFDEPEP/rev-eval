"""Pure, deterministic scoring core for quiz answers (W3-F2).

Two leaf scorers — :mod:`exact_match` (single-select: ``mcq``/``true_false``)
and :mod:`partial_credit` (multi-select: ``multi``) — each expose the same
``score_question(question_type, correct_answers, submitted_answers)`` signature
and return a :class:`ScoreResult`. Neither touches the database or the network,
so they are trivially unit-testable.

:func:`score` is the single dispatch site the answer endpoint calls: it routes
by ``question_type`` to the right scorer.
"""
from typing import List

from src.scoring import exact_match, partial_credit
from src.scoring.result import ScoreResult

__all__ = ["ScoreResult", "score"]

# Question types that are scored by exact set equality.
_EXACT_TYPES = {"mcq", "true_false"}
# Question types scored with partial credit (Jaccard).
_PARTIAL_TYPES = {"multi"}


def score(
    question_type: str,
    correct_answers: List,
    submitted_answers: List,
) -> ScoreResult:
    """Dispatch to the scorer for ``question_type``.

    ``mcq``/``true_false`` → exact match; ``multi`` → partial credit. Any other
    type (e.g. free-text ``text``) is not auto-scorable: it is recorded with a
    ``0.0`` score awaiting manual review (W4), and never blocks the candidate
    from advancing.
    """
    qtype = (question_type or "").lower()
    if qtype in _EXACT_TYPES:
        return exact_match.score_question(qtype, correct_answers, submitted_answers)
    if qtype in _PARTIAL_TYPES:
        return partial_credit.score_question(qtype, correct_answers, submitted_answers)
    # Not auto-scorable (e.g. text) — recorded, manual review deferred to W4.
    return ScoreResult(score=0.0, is_correct=False)
