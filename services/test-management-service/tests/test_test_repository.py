"""Repository-layer tests for TestRepository against a hermetic in-memory DB.

Uses the async `db_session` fixture from conftest.py (aiosqlite, no Postgres).
Covers: create, get_by_id, list_all, update, delete, list_by_creator.
"""
from src.models.test import Test, TestType
from src.repositories.test_repository import TestRepository
from src.schemas.test_schema import TestCreate, TestUpdate


def _make_create(**kw) -> TestCreate:
    defaults = dict(
        name="Python Basics",
        test_type=TestType.QUIZ,
        role="Junior Developer",
        duration_seconds=2700,
        number_of_questions=20,
        active=True,
        created_by_id=1,
    )
    defaults.update(kw)
    return TestCreate(**defaults)


async def test_create_then_get_by_id(db_session):
    created = await TestRepository.create(db_session, _make_create())
    assert created.id is not None
    assert created.name == "Python Basics"

    fetched = await TestRepository.get_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.name == "Python Basics"
    assert fetched.role == "Junior Developer"


async def test_get_by_id_missing_returns_none(db_session):
    result = await TestRepository.get_by_id(db_session, 9999)
    assert result is None


async def test_list_all_returns_all_tests(db_session):
    await TestRepository.create(db_session, _make_create(name="Test A"))
    await TestRepository.create(db_session, _make_create(name="Test B"))

    tests = await TestRepository.list_all(db_session)
    names = [t.name for t in tests]
    assert "Test A" in names
    assert "Test B" in names
    assert len(tests) == 2


async def test_update_mutates_fields(db_session):
    created = await TestRepository.create(db_session, _make_create())
    update = TestUpdate(name="Updated Name", role="Senior Developer")
    updated = await TestRepository.update(db_session, created, update)

    assert updated.name == "Updated Name"
    assert updated.role == "Senior Developer"
    assert updated.number_of_questions == 20  # unchanged


async def test_delete_removes_record(db_session):
    created = await TestRepository.create(db_session, _make_create())
    test_id = created.id

    await TestRepository.delete(db_session, created)

    assert await TestRepository.get_by_id(db_session, test_id) is None


async def test_list_by_creator_filters_correctly(db_session):
    await TestRepository.create(db_session, _make_create(name="By Alice", created_by_id=1))
    await TestRepository.create(db_session, _make_create(name="By Alice 2", created_by_id=1))
    await TestRepository.create(db_session, _make_create(name="By Bob", created_by_id=2))

    alice_tests = await TestRepository.list_by_creator(db_session, 1)
    bob_tests = await TestRepository.list_by_creator(db_session, 2)

    assert len(alice_tests) == 2
    assert all(t.created_by_id == 1 for t in alice_tests)
    assert len(bob_tests) == 1
    assert bob_tests[0].name == "By Bob"
