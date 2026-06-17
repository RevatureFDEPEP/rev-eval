"""Repository-level tests for TestRepository.get_by_id (W5-F2).

Real SQLAlchemy reads against the hermetic in-memory SQLite ``db_session``
fixture (service-root conftest.py) — no Postgres, no Alembic. Covers the
None-row guard (missing id must return None, not raise AttributeError -> 500)
plus the duration / no-duration branches on a found row.
"""
from datetime import timedelta

from src.models.test import Test
from src.repositories.test_repository import TestRepository


async def _make_test(db_session, name="Quiz", duration=None):
    test = Test(name=name, number_of_questions=5, duration=duration)
    db_session.add(test)
    await db_session.commit()
    await db_session.refresh(test)
    return test


async def test_get_by_id_missing_returns_none(db_session):
    # No rows inserted: a missing id must return None, never raise.
    assert await TestRepository.get_by_id(db_session, 999999) is None


async def test_get_by_id_with_duration_sets_seconds(db_session):
    created = await _make_test(db_session, duration=timedelta(seconds=900))
    fetched = await TestRepository.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.duration_seconds == 900


async def test_get_by_id_without_duration_sets_none(db_session):
    created = await _make_test(db_session, duration=None)
    fetched = await TestRepository.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.duration_seconds is None
