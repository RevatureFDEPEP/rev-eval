"""Pure unit tests for the W3-F2 scoring engine (``src.scoring.engine``).

No async, no DB, no httpx, no clock — ``score_question`` is a pure function, so
every case here is a flat table of (inputs -> expected ``score`` / ``is_correct``)
derived directly from the engine docstring's stated semantics:

* single-select (``mcq`` / ``true_false`` / unknown type) is all-or-nothing on
  set equality;
* ``multi`` is Jaccard partial credit ``|A∩B| / |A∪B|`` with ``is_correct`` True
  only when the score is exactly ``1.0``;
* both lists are normalized to a ``frozenset`` at the boundary, so order and
  duplicates never change the score, and ``None``/``[]`` both become the empty
  set;
* the empty/empty degenerate case scores ``1.0`` for BOTH branches.

Expected values are computed by hand from the contract, not read off the
implementation (verify-and-own).
"""

import pytest
from src.scoring.engine import ScoreResult, score_question


# ---------------------------------------------------------------------------
# Single-select: mcq / true_false -> exact match, all-or-nothing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "qtype, correct, submitted, exp_score, exp_correct",
    [
        # mcq exact match
        ("mcq", [2], [2], 1.0, True),
        # mcq mismatch -> 0.0
        ("mcq", [2], [1], 0.0, False),
        # mcq: submitting extra option is NOT an exact match
        ("mcq", [2], [1, 2], 0.0, False),
        # true_false exact match (True)
        ("true_false", [True], [True], 1.0, True),
        # true_false wrong choice
        ("true_false", [True], [False], 0.0, False),
        # scalar (not a list) submitted -> wrapped to a one-element set, matches
        ("true_false", True, True, 1.0, True),
        # scalar mismatch
        ("mcq", 2, 1, 0.0, False),
    ],
    ids=[
        "mcq-exact-match",
        "mcq-wrong",
        "mcq-extra-option-not-exact",
        "true_false-true-match",
        "true_false-wrong",
        "true_false-scalar-match",
        "mcq-scalar-mismatch",
    ],
)
def test_single_select_exact_match(qtype, correct, submitted, exp_score, exp_correct):
    result = score_question(qtype, correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.score == exp_score
    assert result.is_correct is exp_correct


# ---------------------------------------------------------------------------
# Multi-select: Jaccard partial credit  |A ∩ B| / |A ∪ B|
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "correct, submitted, exp_score, exp_correct",
    [
        # full match -> 1.0, is_correct True
        (["a", "b", "c"], ["a", "b", "c"], 1.0, True),
        # correct {a,b,c}, submitted {a,b}: |∩|=2, |∪|=3 -> 2/3
        (["a", "b", "c"], ["a", "b"], 2 / 3, False),
        # correct {a,b}, submitted {a,c}: |∩|=1, |∪|=3 -> 1/3
        (["a", "b"], ["a", "c"], 1 / 3, False),
        # one of two correct, no wrong: |∩|=1, |∪|=2 -> 1/2
        (["a", "b"], ["a"], 1 / 2, False),
        # one correct plus one wrong: |∩|=1, |∪|=3 -> 1/3
        (["a", "b"], ["a", "x"], 1 / 3, False),
        # nothing right: |∩|=0 -> 0.0
        (["a", "b"], ["x", "y"], 0.0, False),
    ],
    ids=[
        "multi-full-match",
        "multi-2of3-jaccard-two-thirds",
        "multi-one-right-one-wrong-third",
        "multi-half",
        "multi-one-right-one-extra-third",
        "multi-all-wrong-zero",
    ],
)
def test_multi_jaccard_partial_credit(correct, submitted, exp_score, exp_correct):
    result = score_question("multi", correct, submitted)
    assert result.score == pytest.approx(exp_score)
    assert result.is_correct is exp_correct


def test_multi_is_correct_only_when_score_is_one():
    """``is_correct`` is True for multi ONLY on an exact set match (score 1.0)."""
    near_miss = score_question("multi", ["a", "b", "c"], ["a", "b"])
    assert near_miss.score < 1.0
    assert near_miss.is_correct is False

    full = score_question("multi", ["a", "b", "c"], ["a", "b", "c"])
    assert full.score == 1.0
    assert full.is_correct is True


def test_multi_select_all_gaming_does_not_score_one():
    """Submitting EVERY option must not earn full credit on multi.

    Correct {a,b} out of options {a,b,c,d,e}; selecting all five gives
    |∩|=2, |∪|=5 -> 2/5 = 0.4. The union grows with the over-selection, so the
    score collapses toward |A|/|options| rather than rewarding the candidate.
    """
    correct = ["a", "b"]
    select_all = ["a", "b", "c", "d", "e"]
    result = score_question("multi", correct, select_all)
    assert result.score == pytest.approx(2 / 5)
    assert result.score < 1.0
    assert result.is_correct is False


# ---------------------------------------------------------------------------
# Order / duplicate insensitivity (frozenset normalization)
# ---------------------------------------------------------------------------
def test_order_and_duplicate_insensitive_multi():
    """[1, 2, 2] and [2, 1] normalize to the same set -> identical score."""
    a = score_question("multi", [1, 2], [1, 2, 2])
    b = score_question("multi", [1, 2], [2, 1])
    assert a.score == b.score == 1.0
    assert a.is_correct is b.is_correct is True


def test_order_and_duplicate_insensitive_single():
    """Single-select exact-match is also order/dup insensitive (set equality)."""
    a = score_question("mcq", [1, 2], [1, 2, 2])
    b = score_question("mcq", [1, 2], [2, 1])
    assert a.score == b.score == 1.0
    assert a.is_correct is b.is_correct is True


# ---------------------------------------------------------------------------
# Edge cases from the docstring
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("qtype", ["multi", "mcq", "true_false"])
@pytest.mark.parametrize("submitted", [None, []])
def test_empty_submission_against_nonempty_correct_is_zero(qtype, submitted):
    """No answer (None or []) vs a non-empty key -> 0.0 / not correct, for both
    the multi (Jaccard) and single-select branches."""
    result = score_question(qtype, ["a", "b"], submitted)
    assert result.score == 0.0
    assert result.is_correct is False


@pytest.mark.parametrize("qtype", ["multi", "mcq", "true_false"])
@pytest.mark.parametrize("correct", [None, []])
@pytest.mark.parametrize("submitted", [None, []])
def test_empty_correct_and_empty_submitted_is_vacuous_full_match(
    qtype, correct, submitted
):
    """Degenerate empty/empty: both branches treat it as a full (vacuous) match
    -> 1.0 / is_correct True (multi via the 0/0 -> 1.0 rule, single via
    ``set() == set()``)."""
    result = score_question(qtype, correct, submitted)
    assert result.score == 1.0
    assert result.is_correct is True


def test_empty_correct_but_nonempty_submitted_multi_is_zero():
    """Empty key, non-empty submission on multi: |∩|=0, |∪|=2 -> 0.0."""
    result = score_question("multi", [], ["a", "b"])
    assert result.score == 0.0
    assert result.is_correct is False


def test_empty_correct_but_nonempty_submitted_single_is_zero():
    """Empty key, non-empty submission on single-select: set() != {a} -> 0.0."""
    result = score_question("mcq", None, ["a"])
    assert result.score == 0.0
    assert result.is_correct is False


def test_heterogeneous_types_compared_as_is_no_coercion():
    """The engine does not coerce: int 1, bool True and str '1' are distinct
    set members, so the answer key's own types decide equality."""
    # Key holds int 1; submitting the string "1" is NOT a match (no coercion).
    mismatch = score_question("mcq", [1], ["1"])
    assert mismatch.score == 0.0
    assert mismatch.is_correct is False

    # Key holds bool True; submitting it back as bool True matches.
    match = score_question("true_false", [True], [True])
    assert match.score == 1.0
    assert match.is_correct is True

    # Mixed-type key compared verbatim against an identical mixed submission.
    mixed = score_question("multi", [1, "a", True], ["a", True, 1])
    assert mixed.score == 1.0
    assert mixed.is_correct is True


# NOTE on int/bool set identity: Python hashes ``True == 1`` and ``False == 0``,
# so {1} and {True} are the same set. The case below documents that the engine
# inherits Python's set semantics here (it does NOT distinguish 1 from True),
# which is the contract's "compared as-is via set membership" behavior.
def test_bool_one_share_python_set_identity():
    result = score_question("mcq", [1], [True])
    assert result.score == 1.0
    assert result.is_correct is True


# ---------------------------------------------------------------------------
# Case-insensitive question_type; unknown / "" / None -> exact-match fallback
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "qtype",
    ["MULTI", "Multi", "  multi  "],
    ids=["upper", "title", "whitespace"],
)
def test_question_type_is_case_and_whitespace_insensitive_for_multi(qtype):
    """'MULTI' / 'Multi' / padded 'multi' all route to the Jaccard branch."""
    result = score_question(qtype, ["a", "b", "c"], ["a", "b"])
    assert result.score == pytest.approx(2 / 3)
    assert result.is_correct is False


@pytest.mark.parametrize("qtype", ["MCQ", "Mcq", "TRUE_FALSE"])
def test_question_type_case_insensitive_for_single(qtype):
    result = score_question(qtype, [2], [2])
    assert result.score == 1.0
    assert result.is_correct is True


@pytest.mark.parametrize(
    "qtype, partial_submit",
    [
        ("unknown_type", True),
        ("", True),
        (None, True),
        ("text", True),
    ],
    ids=["unknown", "empty-string", "none", "text"],
)
def test_unknown_or_none_type_falls_back_to_exact_match(qtype, partial_submit):
    """Any non-'multi' type (unknown / '' / None / text) uses the exact-match
    rule: a partial submission is NOT credited (single-select all-or-nothing),
    proving it did NOT silently take the Jaccard branch."""
    # correct {a,b,c}, submitted {a,b}: Jaccard would give 2/3; exact gives 0.0.
    result = score_question(qtype, ["a", "b", "c"], ["a", "b"])
    assert result.score == 0.0
    assert result.is_correct is False

    # the same fallback type still credits an exact match
    exact = score_question(qtype, ["a", "b", "c"], ["a", "b", "c"])
    assert exact.score == 1.0
    assert exact.is_correct is True
