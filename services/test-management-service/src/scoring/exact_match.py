"""Exact-match scoring for single-select questions (``mcq``, ``true_false``).

A *pure* function: no database access, no network, no side effects — so the
bulk of scoring coverage (W3-F2 step 5) needs no fixtures. The answer endpoint
calls this through the :mod:`src.scoring` dispatch; it is never given DB rows.
"""
from typing import List

from src.scoring.result import ScoreResult


def score_question(
    question_type: str,
    correct_answers: List,
    submitted_answers: List,
) -> ScoreResult:
    """Score a single-select answer by exact set equality.

    A single-select question has exactly one correct choice, but both sides are
    treated as sets so order and accidental duplicates do not matter. The answer
    is correct (score ``1.0``) only when the submitted set equals the correct
    set; anything else — wrong choice, no choice, or multiple choices — scores
    ``0.0``.
    """
    correct = set(correct_answers or [])
    submitted = set(submitted_answers or [])
    is_correct = submitted == correct and len(correct) > 0
    return ScoreResult(score=1.0 if is_correct else 0.0, is_correct=is_correct)
