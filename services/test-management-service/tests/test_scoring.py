"""
Parameterized tests for the scoring module.

Covers:
- exact_match.score_question: MCQ single-answer, true/false, full-match multi-select
- partial_credit.score_question: Jaccard similarity across various overlap ratios
- Edge cases: empty lists, case normalisation, whitespace stripping
"""
import pytest
from src.scoring import exact_match, partial_credit
from src.scoring.models import ScoreResult

# ─────────────────────────────────────────────────────────────────────────────
# exact_match
# ─────────────────────────────────────────────────────────────────────────────

EXACT_MATCH_CASES = [
    # (question_type, correct_answers, submitted_answers, expected_score, expected_is_correct)
    # ── MCQ / single-select ──────────────────────────────────────────────────
    pytest.param("mcq", ["B"], ["B"], 1.0, True, id="mcq-correct"),
    pytest.param("mcq", ["B"], ["A"], 0.0, False, id="mcq-wrong"),
    pytest.param("mcq", ["yes"], ["YES"], 1.0, True, id="mcq-case-insensitive"),
    pytest.param("mcq", ["  A  "], ["A"], 1.0, True, id="mcq-strip-whitespace"),
    pytest.param("mcq", ["A"], [], 0.0, False, id="mcq-no-submission"),
    pytest.param("mcq", [], ["A"], 0.0, False, id="mcq-no-correct"),
    pytest.param("true_false", ["True"], ["true"], 1.0, True, id="true_false-correct"),
    pytest.param("true_false", ["True"], ["False"], 0.0, False, id="true_false-wrong"),
    pytest.param("single_select", ["C"], ["C"], 1.0, True, id="single_select-correct"),
    # ── Multi-select full-match ──────────────────────────────────────────────
    pytest.param("multiple_select", ["A", "B"], ["A", "B"], 1.0, True, id="multi-exact-match"),
    pytest.param("multiple_select", ["A", "B"], ["B", "A"], 1.0, True, id="multi-order-independent"),
    pytest.param("multiple_select", ["A", "B"], ["A"], 0.0, False, id="multi-missing-one"),
    pytest.param("multiple_select", ["A", "B"], ["A", "B", "C"], 0.0, False, id="multi-extra-answer"),
    pytest.param("multiple_select", ["A", "B", "C"], ["A"], 0.0, False, id="multi-mostly-wrong"),
    pytest.param("multi_select", ["X", "Y"], ["X", "Y"], 1.0, True, id="multi_select-correct"),
    pytest.param("checkbox", ["opt1", "opt2"], ["opt1"], 0.0, False, id="checkbox-partial-not-full"),
    # ── Unrecognised type defaults to single exact match ─────────────────────
    pytest.param("unknown_type", ["42"], ["42"], 1.0, True, id="unknown-type-exact"),
    pytest.param("unknown_type", ["42"], ["43"], 0.0, False, id="unknown-type-wrong"),
]


@pytest.mark.parametrize("question_type,correct,submitted,exp_score,exp_correct", EXACT_MATCH_CASES)
def test_exact_match(question_type, correct, submitted, exp_score, exp_correct):
    result = exact_match.score_question(question_type, correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.score == pytest.approx(exp_score)
    assert result.is_correct is exp_correct
    assert result.points_possible == pytest.approx(1.0)
    assert result.points_earned == pytest.approx(exp_score)


# ─────────────────────────────────────────────────────────────────────────────
# partial_credit (Jaccard)
# ─────────────────────────────────────────────────────────────────────────────

PARTIAL_CREDIT_CASES = [
    # (question_type, correct_answers, submitted_answers, expected_score, expected_is_correct)
    # ── Perfect match ────────────────────────────────────────────────────────
    pytest.param("multiple_select", ["A", "B", "C"], ["A", "B", "C"], 1.0, True, id="jaccard-perfect"),
    pytest.param("text", ["hello"], ["HELLO"], 1.0, True, id="jaccard-case-insensitive"),
    pytest.param("text", ["  hi  "], ["hi"], 1.0, True, id="jaccard-whitespace"),
    # ── Partial overlap ──────────────────────────────────────────────────────
    # |{A,B} ∩ {A}| / |{A,B} ∪ {A}| = 1/2 = 0.5
    pytest.param("multiple_select", ["A", "B"], ["A"], 0.5, False, id="jaccard-half"),
    # |{A,B,C} ∩ {A,B}| / |{A,B,C} ∪ {A,B}| = 2/3
    pytest.param("multiple_select", ["A", "B", "C"], ["A", "B"], 2 / 3, False, id="jaccard-two-of-three"),
    # ── No overlap ───────────────────────────────────────────────────────────
    pytest.param("multiple_select", ["A", "B"], ["C", "D"], 0.0, False, id="jaccard-no-overlap"),
    pytest.param("text", ["apple"], ["orange"], 0.0, False, id="jaccard-text-miss"),
    # ── Extra answers penalised via union ────────────────────────────────────
    # |{A} ∩ {A,B}| / |{A} ∪ {A,B}| = 1/2 = 0.5
    pytest.param("multiple_select", ["A"], ["A", "B"], 0.5, False, id="jaccard-extra-penalised"),
    # ── Empty sets ───────────────────────────────────────────────────────────
    pytest.param("multiple_select", [], [], 1.0, True, id="jaccard-both-empty"),
    # |{A} ∩ {}| / |{A} ∪ {}| = 0/1 = 0.0
    pytest.param("multiple_select", ["A"], [], 0.0, False, id="jaccard-submitted-empty"),
    pytest.param("multiple_select", [], ["A"], 0.0, False, id="jaccard-correct-empty"),
]


@pytest.mark.parametrize("question_type,correct,submitted,exp_score,exp_correct", PARTIAL_CREDIT_CASES)
def test_partial_credit(question_type, correct, submitted, exp_score, exp_correct):
    result = partial_credit.score_question(question_type, correct, submitted)
    assert isinstance(result, ScoreResult)
    assert result.score == pytest.approx(exp_score, rel=1e-6)
    assert result.is_correct is exp_correct
    assert result.points_possible == pytest.approx(1.0)
    assert result.points_earned == pytest.approx(exp_score, rel=1e-6)
    assert isinstance(result.details, str)
    assert len(result.details) > 0


# ─────────────────────────────────────────────────────────────────────────────
# ScoreResult dataclass sanity
# ─────────────────────────────────────────────────────────────────────────────

def test_score_result_defaults():
    r = ScoreResult(score=0.75, is_correct=False, points_earned=0.75)
    assert r.points_possible == 1.0
    assert r.details == ""


def test_score_result_full():
    r = ScoreResult(score=1.0, is_correct=True, points_earned=1.0, points_possible=2.0, details="ok")
    assert r.points_possible == 2.0
    assert r.details == "ok"
