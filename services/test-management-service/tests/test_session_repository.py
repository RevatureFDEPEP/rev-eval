"""Repository-level tests for SessionRepository against a hermetic DB.

Real SQLAlchemy CRUD against the in-memory SQLite `db_session` fixture
(root conftest.py) — no Postgres, no Alembic. Covers create/get_by_id/
get_by_token and get_test (the direct-select that dodges
TestRepository.get_by_id's None-crash on a missing id).
"""
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.session import Session, SessionStatus
from src.models.test import Test
from src.repositories.session_repository import SessionRepository


async def _make_session(db_session, token="tok", test_id=1):
    now = datetime.utcnow()
    session = Session(
        session_id=uuid4(),
        test_id=test_id,
        user_id=42,
        session_token=token,
        server_now=now,
        expires_at=now + timedelta(hours=1),
        status=SessionStatus.ACTIVE,
        current_index=0,
        question_ids=["a", "b"],
    )
    return await SessionRepository.create(db_session, session)


async def test_create_then_get_by_id(db_session):
    created = await _make_session(db_session)
    assert created.session_id is not None

    fetched = await SessionRepository.get_by_id(db_session, created.session_id)
    assert fetched is not None
    assert fetched.question_ids == ["a", "b"]
    assert fetched.status == SessionStatus.ACTIVE


async def test_get_by_token(db_session):
    created = await _make_session(db_session, token="opaque-hex")
    fetched = await SessionRepository.get_by_token(db_session, "opaque-hex")
    assert fetched is not None
    assert fetched.session_id == created.session_id


async def test_get_by_token_missing_returns_none(db_session):
    assert await SessionRepository.get_by_token(db_session, "nope") is None


async def test_get_test_found(db_session):
    test = Test(name="Quiz", number_of_questions=5, duration=timedelta(seconds=900))
    db_session.add(test)
    await db_session.commit()
    await db_session.refresh(test)

    fetched = await SessionRepository.get_test(db_session, test.id)
    assert fetched is not None
    assert fetched.number_of_questions == 5
    assert fetched.duration == timedelta(seconds=900)


async def test_get_test_missing_returns_none(db_session):
    # The defect-dodging path: a missing id returns None, not an AttributeError.
    assert await SessionRepository.get_test(db_session, 9999) is None
