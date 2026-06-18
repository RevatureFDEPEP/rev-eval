"""Deterministic, side-effect-free scoring engine (W3-F2).

``score_question(question_type, correct_answers, submitted_answers) -> ScoreResult``
is a *pure* function: no DB, no clock, no httpx, no global state. It normalizes
both answer lists to a ``frozenset`` at the boundary (so order and duplicates
never affect the score), then applies a per-type algorithm:

* **Single-select** (``mcq`` / ``true_false`` / any exact-match type): the score
  is ``1.0`` iff the submitted set equals the correct set, else ``0.0``. This is
  the Day-12 deterministic exact-match rule; it makes a single-select question
  all-or-nothing, which is what a single right answer should be.

* **Multi-select** (``multi``): **partial credit via the Jaccard index**
  ``|A ∩ B| / |A ∪ B|`` (intersection over union of the correct set ``A`` and the
  submitted set ``B``). ``is_correct`` is ``True`` only when the score is exactly
  ``1.0`` (an exact set match).

Why Jaccard for partial credit (ADR-worthy choice): of the three defensible
multi-select algorithms (full-match, Jaccard, set-overlap), Jaccard is symmetric
in the two failure modes a learner can make — *missing* a correct option and
*adding* an incorrect one both enlarge the union without enlarging the
intersection, so both are penalized. That makes "select everything" gaming
ineffective: picking every option drives the union to the full option set while
the intersection stays at ``|A|``, so the score collapses toward
``|A| / |options|`` rather than rewarding the candidate. It is bounded in
``[0, 1]``, deterministic, and explainable as a single ratio. (Set-overlap —
``max(0, (correct_selected - incorrect_selected) / |correct|)`` — is the other
strong option and the one the PEP doc leans toward; we choose Jaccard here per
the W3-F2 spec and record set-overlap as the alternative for the ADR.)

Edge cases (all handled without raising):
* empty / ``None`` ``submitted_answers`` -> empty set -> score ``0.0`` (the
  candidate answered nothing) for any non-empty correct set.
* empty / ``None`` ``correct_answers`` *and* empty submitted -> both sets empty
  -> Jaccard is defined as ``1.0`` here (``0/0`` -> treat the empty/empty match
  as a full match) and exact-match is also ``1.0`` (``set() == set()``); this is
  a degenerate authoring case, not a normal scored question.
* heterogeneous element types (``int`` / ``bool`` / ``str``) are compared as-is
  via set membership — the engine does not coerce, so the answer key's own types
  (qms stores ``list[int | bool | str]``) decide equality.

Answer-encoding contract (the engine compares ``correct_answers`` and
``submitted_answers`` as raw sets with NO coercion, so both sides must use the
same encoding or the score silently collapses to 0.0):

* ``mcq`` / ``multi`` — **1-indexed integer ``option_id``s**. qms stores
  ``correct_answers`` as the 1-indexed positions of the options (numbered from
  1), so the candidate's ``submitted_answers`` must also be those 1-indexed
  ``option_id`` ints — not 0-indexed array indices and not option text. Submit
  ``[2]`` for the second option. (See ``AnswerSubmit`` for the wire contract the
  TestRunner must honor.)
* ``true_false`` — a single ``bool`` (matching the boolean qms stores).
* ``text`` — not auto-scored here (essay/short-answer placeholder).
"""

from dataclasses import dataclass
from typing import Any

# Question-type tags as stored by question-management-service (StrEnum values).
MCQ = "mcq"
MULTI = "multi"
TRUE_FALSE = "true_false"
TEXT = "text"


@dataclass(frozen=True)
class ScoreResult:
    """The outcome of scoring one answer.

    ``score`` is a float in ``[0.0, 1.0]`` (fraction of credit earned).
    ``is_correct`` is ``True`` only on a full match (``score == 1.0``).
    Immutable so a result cannot be mutated after it is computed/persisted.
    """

    score: float
    is_correct: bool


def _to_set(values: Any) -> frozenset:
    """Normalize a list / scalar / ``None`` to a ``frozenset`` at the boundary.

    Order and duplicates are discarded so ``[1, 2, 2]`` and ``[2, 1]`` score
    identically. ``None`` (no answer key / no submission) and an empty list both
    become the empty set. A bare scalar (e.g. a single ``True`` for true/false)
    is wrapped so callers may pass either ``True`` or ``[True]``.

    ``bool`` is intentionally NOT iterated (it is not a sequence); strings are
    treated as a single scalar element, never iterated character-by-character.
    """
    if values is None:
        return frozenset()
    if isinstance(values, (list, tuple, set, frozenset)):
        return frozenset(values)
    # A scalar answer (int / bool / str) -> a one-element set.
    return frozenset([values])


def _jaccard(correct: frozenset, submitted: frozenset) -> float:
    """Jaccard index ``|A ∩ B| / |A ∪ B|`` with the empty/empty case as ``1.0``."""
    union = correct | submitted
    if not union:
        # Both empty: degenerate, treat as a full (vacuous) match.
        return 1.0
    intersection = correct & submitted
    return len(intersection) / len(union)


def score_question(
    question_type: str,
    correct_answers: Any,
    submitted_answers: Any,
) -> ScoreResult:
    """Score one submitted answer against its correct-answer key.

    Pure and deterministic. ``question_type`` is matched case-insensitively
    against the qms type tags; anything that is not ``multi`` is scored with the
    exact-match (single-select) rule, which is the safe default for
    ``mcq`` / ``true_false`` and any future single-answer type.
    """
    correct = _to_set(correct_answers)
    submitted = _to_set(submitted_answers)
    qtype = (question_type or "").strip().lower()

    if qtype == MULTI:
        score = _jaccard(correct, submitted)
        return ScoreResult(score=score, is_correct=score == 1.0)

    # Single-select / true_false / exact-match: all-or-nothing on set equality.
    is_correct = correct == submitted
    return ScoreResult(score=1.0 if is_correct else 0.0, is_correct=is_correct)
