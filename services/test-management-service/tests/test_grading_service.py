"""Unit tests for the trainer manual-grading service (W5-F1).

Repositories + the DB session are patched (no DB, no network), matching the
AsyncMock style of the session-service suite. Covers the grade happy path
(score/is_correct/status mutation + needs_grading recompute) and the
not-pending rejection.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.models.answer import GradingStatus
from src.services.grading_service import (
    AnswerNotFoundError,
    AnswerNotPendingError,
    GradingService,
)

SVC = "src.services.grading_service"
SID = uuid4()


def _answer(status=GradingStatus.PENDING_REVIEW):
    return SimpleNamespace(
        id=7,
        session_id=SID,
        question_index=2,
        score=0.0,
        is_correct=False,
        feedback=None,
        graded_by_id=None,
        graded_at=None,
        grading_status=status,
    )


def _grade(answer, *, score=0.75, feedback="good", remaining=0, grader=9):
    db = AsyncMock()
    session = SimpleNamespace(needs_grading=True)
    with patch(f"{SVC}.AnswerRepository.get_by_slot", new_callable=AsyncMock) as gbs, \
         patch(f"{SVC}.AnswerRepository.count_pending", new_callable=AsyncMock) as cp, \
         patch(f"{SVC}.SessionRepository.get_for_update", new_callable=AsyncMock) as gfu, \
         patch(f"{SVC}.SessionRepository.flush", new_callable=AsyncMock):
        gbs.return_value = answer
        cp.return_value = remaining
        gfu.return_value = session
        try:
            out = asyncio.run(
                GradingService.grade_answer(db, SID, 2, score, feedback, grader)
            )
        except Exception as e:  # noqa: BLE001
            return e, answer, session, db
    return out, answer, session, db


def test_grade_sets_score_status_and_clears_needs_grading():
    out, answer, session, db = _grade(_answer(), score=0.75, remaining=0)
    assert answer.score == 0.75
    assert answer.is_correct is False  # not a perfect score
    assert answer.grading_status == GradingStatus.GRADED
    assert answer.graded_by_id == 9
    assert answer.graded_at is not None
    assert session.needs_grading is False
    assert out.session_needs_grading is False
    assert out.grading_status == "GRADED"
    db.commit.assert_awaited_once()


def test_perfect_score_marks_is_correct():
    _out, ans, _session, _db = _grade(_answer(), score=1.0)
    assert ans.is_correct is True


def test_needs_grading_stays_true_when_more_pending():
    _out, _ans, session, _db = _grade(_answer(), remaining=2)
    assert session.needs_grading is True


def test_regrade_already_graded_is_allowed():
    out, ans, _session, _db = _grade(_answer(GradingStatus.GRADED), score=0.4)
    assert ans.score == 0.4
    assert out.grading_status == "GRADED"


def test_auto_scored_answer_rejected():
    err, _ans, _s, _db = _grade(_answer(GradingStatus.AUTO))
    assert isinstance(err, AnswerNotPendingError)


def test_missing_answer_404():
    db = AsyncMock()
    with patch(f"{SVC}.AnswerRepository.get_by_slot", new_callable=AsyncMock) as gbs:
        gbs.return_value = None
        with pytest.raises(AnswerNotFoundError):
            asyncio.run(GradingService.grade_answer(db, SID, 2, 0.5, None, 9))
