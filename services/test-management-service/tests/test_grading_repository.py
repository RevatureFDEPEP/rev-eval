"""Repository-level tests for the grading queries (W5-F1) against sqlite.

Real CRUD over the in-memory ``db_session`` fixture (root conftest): covers
AnswerRepository.list_pending (join + filter + paging), count_pending, get and
get_by_slot.
"""
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.answer import Answer, GradingStatus
from src.models.session import Session, SessionStatus
from src.models.test import Test
from src.repositories.answer_repository import AnswerRepository


async def _session(db, test_id, *, token):
    now = datetime.utcnow()
    s = Session(
        session_id=uuid4(),
        test_id=test_id,
        user_id=42,
        session_token=token,
        server_now=now,
        expires_at=now + timedelta(hours=1),
        status=SessionStatus.SUBMITTED,
        current_index=1,
        question_ids=["q0", "q1"],
        submitted_at=now,
    )
    db.add(s)
    await db.flush()
    return s


async def _seed(db):
    db.add(Test(name="Java Quiz", number_of_questions=2, duration=timedelta(seconds=900)))
    await db.flush()
    s = await _session(db, 1, token="t1")
    db.add_all([
        Answer(session_id=s.session_id, question_id="q0", question_index=0,
               submitted_answers=[1], score=1.0, is_correct=True,
               grading_status=GradingStatus.AUTO),
        Answer(session_id=s.session_id, question_id="q1", question_index=1,
               submitted_answers=["prose"], score=0.0, is_correct=False,
               grading_status=GradingStatus.PENDING_REVIEW),
    ])
    await db.flush()
    return s


async def test_list_pending_returns_only_pending_with_test_name(db_session):
    await _seed(db_session)
    rows, total = await AnswerRepository.list_pending(db_session)
    assert total == 1
    answer, user_id, test_id, submitted_at, test_name = rows[0]
    assert answer.grading_status == GradingStatus.PENDING_REVIEW
    assert answer.question_index == 1
    assert user_id == 42
    assert test_id == 1
    assert test_name == "Java Quiz"
    assert submitted_at is not None


async def test_list_pending_test_filter_excludes_others(db_session):
    await _seed(db_session)
    rows, total = await AnswerRepository.list_pending(db_session, test_id=999)
    assert total == 0
    assert rows == []


async def test_count_pending_and_get_helpers(db_session):
    s = await _seed(db_session)
    assert await AnswerRepository.count_pending(db_session, s.session_id) == 1

    slot = await AnswerRepository.get_by_slot(db_session, s.session_id, 1)
    assert slot is not None and slot.grading_status == GradingStatus.PENDING_REVIEW
    assert await AnswerRepository.get(db_session, slot.id) is not None
    assert await AnswerRepository.get_by_slot(db_session, s.session_id, 5) is None
