import pytest
from src.repositories.test_repository import TestRepository
from src.schemas.test_schema import TestCreate, TestUpdate
from src.models.test import TestType


class TestTestRepository:
    async def test_create_test(self, db):
        test = await TestRepository.create(db, TestCreate(name="Java Quiz", test_type=TestType.QUIZ))
        assert test.id is not None
        assert test.name == "Java Quiz"
        assert test.test_type == TestType.QUIZ

    async def test_create_sets_defaults(self, db):
        test = await TestRepository.create(db, TestCreate(name="Defaults", test_type=TestType.QUIZ))
        assert test.active is True
        assert test.number_of_questions == 20

    async def test_create_with_creator_id(self, db):
        test = await TestRepository.create(
            db, TestCreate(name="Creator Test", test_type=TestType.QUIZ, created_by_id=7)
        )
        assert test.created_by_id == 7

    async def test_get_by_id_found(self, db):
        created = await TestRepository.create(db, TestCreate(name="Find Me", test_type=TestType.QUIZ))
        found = await TestRepository.get_by_id(db, created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_id_not_found_returns_none(self, db):
        result = await TestRepository.get_by_id(db, 99999)
        assert result is None

    async def test_list_all_empty(self, db):
        tests = await TestRepository.list_all(db)
        assert tests == []

    async def test_list_all_returns_all(self, db):
        await TestRepository.create(db, TestCreate(name="Test A", test_type=TestType.QUIZ))
        await TestRepository.create(db, TestCreate(name="Test B", test_type=TestType.INTERVIEW))
        tests = await TestRepository.list_all(db)
        assert len(tests) == 2

    async def test_update_name(self, db):
        test = await TestRepository.create(db, TestCreate(name="Old Name", test_type=TestType.QUIZ))
        updated = await TestRepository.update(db, test, TestUpdate(name="New Name"))
        assert updated.name == "New Name"

    async def test_update_active_flag(self, db):
        test = await TestRepository.create(db, TestCreate(name="Active Test", test_type=TestType.QUIZ))
        updated = await TestRepository.update(db, test, TestUpdate(active=False))
        assert updated.active is False

    async def test_update_number_of_questions(self, db):
        test = await TestRepository.create(db, TestCreate(name="Q Test", test_type=TestType.QUIZ))
        updated = await TestRepository.update(db, test, TestUpdate(number_of_questions=30))
        assert updated.number_of_questions == 30

    async def test_delete_removes_test(self, db):
        test = await TestRepository.create(db, TestCreate(name="Delete Me", test_type=TestType.QUIZ))
        test_id = test.id
        await TestRepository.delete(db, test)
        result = await TestRepository.get_by_id(db, test_id)
        assert result is None

    async def test_list_by_creator_filters_correctly(self, db):
        await TestRepository.create(db, TestCreate(name="C1 T1", test_type=TestType.QUIZ, created_by_id=10))
        await TestRepository.create(db, TestCreate(name="C1 T2", test_type=TestType.QUIZ, created_by_id=10))
        await TestRepository.create(db, TestCreate(name="C2 T1", test_type=TestType.QUIZ, created_by_id=99))
        tests = await TestRepository.list_by_creator(db, 10)
        assert len(tests) == 2
        assert all(t.created_by_id == 10 for t in tests)

    async def test_list_by_creator_no_results(self, db):
        tests = await TestRepository.list_by_creator(db, 999)
        assert tests == []

    @pytest.mark.parametrize("test_type", [TestType.QUIZ, TestType.INTERVIEW])
    async def test_create_both_test_types(self, db, test_type):
        test = await TestRepository.create(
            db, TestCreate(name=f"{test_type} Test", test_type=test_type)
        )
        assert test.test_type == test_type
