"""Pure, side-effect-free scoring functions for quiz questions.

No database access, no I/O — trivially unit-testable. The answer service
calls score_question with the correct answers pulled from the per-session
question snapshot.
"""
from .exact_match import score_exact_match
from .partial_credit import score_partial_credit
from .types import ScoreResult

_EXACT_MATCH_TYPES = {"mcq", "true_false"}
_PARTIAL_CREDIT_TYPES = {"multi"}


def score_question(question_type: str, correct_answers, submitted_answers) -> ScoreResult:
    """Dispatch to the scoring algorithm for the given question type.

    Raises ValueError for unknown types. 'text' is non-auto-scorable and
    returns a zero-possible result flagged for manual grading.
    """
    qt = (question_type or "").lower()

    if qt in _EXACT_MATCH_TYPES:
        return score_exact_match(correct_answers, submitted_answers)
    if qt in _PARTIAL_CREDIT_TYPES:
        return score_partial_credit(correct_answers, submitted_answers)
    if qt == "text":
        return ScoreResult(
            earned=0.0,
            possible=0.0,
            is_correct=False,
            details={"reason": "text questions require manual grading"},
        )

    raise ValueError(f"Unsupported question_type: {question_type!r}")


__all__ = [
    "ScoreResult",
    "score_question",
    "score_exact_match",
    "score_partial_credit",
]
