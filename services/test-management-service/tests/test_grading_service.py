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


def _pending_row():
    answer = SimpleNamespace(
        id=7, session_id=SID, question_index=1, question_id="q-mongo",
        submitted_answers=["prose"], grading_status=GradingStatus.PENDING_REVIEW,
    )
    return (answer, 42, 1, None, "Java Quiz")


def _list_queue(question=None, raise_fetch=False):
    db = AsyncMock()

    async def _get_question(_qid):
        if raise_fetch:
            raise RuntimeError("question-service down")
        return question or {"question_text": "Explain X", "sample_answer": "Y"}

    with patch(f"{SVC}.AnswerRepository.list_pending", new_callable=AsyncMock) as lp, \
         patch(f"{SVC}.question_client.get_question", side_effect=_get_question):
        lp.return_value = ([_pending_row()], 1)
        return asyncio.run(GradingService.list_queue(db, test_id=1, page=1, size=20))


def test_list_queue_enriches_with_question_metadata():
    out = _list_queue()
    assert out.total == 1 and out.page == 1 and out.size == 20
    item = out.items[0]
    assert item.answer_id == 7
    assert item.test_name == "Java Quiz"
    assert item.question_text == "Explain X"
    assert item.sample_answer == "Y"


def test_list_queue_tolerates_question_fetch_failure():
    out = _list_queue(raise_fetch=True)
    item = out.items[0]
    assert item.question_text is None  # enrichment is best-effort
    assert item.submitted_answers == ["prose"]
