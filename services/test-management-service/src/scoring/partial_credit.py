"""Partial-credit scoring for multi-select questions (``multi``).

A *pure* function — no DB, no network, no side effects (W3-F2 step 5).

ADR (required for W4-F5 — scoring-algorithm decision)
-----------------------------------------------------
We award partial credit by the **Jaccard index** of the correct and submitted
option sets::

    score = |correct ∩ submitted| / |correct ∪ submitted|

Rationale, versus the alternatives considered:

* **All-or-nothing** (1.0 iff sets match, else 0.0) — discards every signal of
  partial knowledge; a candidate who picks 3 of 4 correct options scores the
  same as one who picks none.
* **Correct-minus-wrong** (``(hits - misses) / |correct|``, floored at 0) —
  graded, but asymmetric and unbounded below before flooring, and it ignores
  the size of the union so spurious picks are under-penalized.
* **Jaccard (chosen)** — bounded ``[0, 1]``, order-independent, and
  *symmetric*: it penalizes both missed correct options (they enlarge the
  union without adding to the intersection) and spurious wrong options (same
  effect). A perfect answer is exactly ``1.0``, which we treat as fully correct.
"""
# AI-assisted (Claude Code); human-reviewed scoring algorithm — see
# docs/ai-assistance.md and ADR docs/adr/0002-multiselect-scoring-algorithm.md.
from typing import List

from src.scoring.result import ScoreResult


def score_question(
    question_type: str,
    correct_answers: List,
    submitted_answers: List,
) -> ScoreResult:
    """Score a multi-select answer by Jaccard overlap (see module ADR).

    ``is_correct`` is reserved for a perfect match (score ``1.0``); any partial
    overlap yields a fractional score with ``is_correct=False``.
    """
    correct = set(correct_answers or [])
    submitted = set(submitted_answers or [])

    if not correct:
        # No correct set to score against — degenerate question; award nothing.
        return ScoreResult(score=0.0, is_correct=False)

    union = correct | submitted
    score = len(correct & submitted) / len(union) if union else 0.0
    return ScoreResult(score=score, is_correct=score == 1.0)
