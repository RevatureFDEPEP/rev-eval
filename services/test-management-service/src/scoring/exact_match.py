"""
Exact-match and full-match scoring.

- Single-answer types (mcq, true_false, single_select): the one submitted
  answer must exactly equal the one correct answer (case-insensitive, stripped).
- Multi-answer types (multiple_select, multi_select, checkbox): every correct
  answer must be present and no extra answers may be present (full-match,
  all-or-nothing).

No database access or side effects.
"""
from typing import Any, List

from src.scoring.models import ScoreResult

_SINGLE_ANSWER_TYPES = {"mcq", "true_false", "single_select", "boolean"}
_MULTI_ANSWER_TYPES = {"multiple_select", "multi_select", "checkbox", "multi_answer"}


def _normalise(answers: List[Any]) -> frozenset:
    return frozenset(str(a).strip().lower() for a in answers)


def score_question(
    question_type: str,
    correct_answers: List[Any],
    submitted_answers: List[Any],
) -> ScoreResult:
    """Return a ScoreResult using exact / full-match logic (all-or-nothing)."""
    qtype = question_type.lower() if question_type else ""

    correct = _normalise(correct_answers)
    submitted = _normalise(submitted_answers)

    if qtype in _SINGLE_ANSWER_TYPES or qtype not in _MULTI_ANSWER_TYPES:
        # For any unrecognised type default to single-answer exact match
        correct_val = next(iter(correct), "")
        submitted_val = next(iter(submitted), "")
        is_correct = correct_val == submitted_val
        score = 1.0 if is_correct else 0.0
        details = "exact match" if is_correct else f"expected {correct_val!r}, got {submitted_val!r}"
    else:
        # Full match: set equality
        is_correct = correct == submitted
        score = 1.0 if is_correct else 0.0
        if is_correct:
            details = "full match"
        else:
            missing = correct - submitted
            extra = submitted - correct
            parts = []
            if missing:
                parts.append(f"missing {sorted(missing)}")
            if extra:
                parts.append(f"extra {sorted(extra)}")
            details = "; ".join(parts)

    return ScoreResult(
        score=score,
        is_correct=is_correct,
        points_earned=score,
        points_possible=1.0,
        details=details,
    )
