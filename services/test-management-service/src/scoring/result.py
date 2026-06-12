# src/scoring/result.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    """Outcome of scoring one answer.

    ``score`` is normalized to ``0.0..max_score`` (``max_score`` is always 1.0
    here — one question is worth one point; aggregation/weighting is a caller
    concern). ``is_correct`` is True only on a full-credit match, so callers can
    branch on correctness without re-deriving it from the float. ``algorithm``
    names the strategy that produced the score for auditability (W4-F5 ADR).
    """

    is_correct: bool
    score: float
    max_score: float = 1.0
    algorithm: str = "exact_match"
