"""Shared scoring result type.

Lives in its own module (not ``__init__``) so the leaf scorers can import it
without a circular dependency on the dispatch package.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    """Outcome of scoring one question.

    ``score`` is a fraction in ``[0.0, 1.0]`` (partial-credit aware).
    ``is_correct`` is reserved for a perfect answer (``score == max_score``).
    """

    score: float
    is_correct: bool
    max_score: float = 1.0
