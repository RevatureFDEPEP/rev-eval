import pytest
from src.models.test import TestType
from src.repositories.test_repository import TestRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.test_schema import TestCreate
from src.schemas.test_submission_schema import (
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
)


async def _make_test(db, name="FK Test"):
    return await TestRepository.create(db, TestCreate(name=name, test_type=TestType.QUIZ))


class TestTestSubmissionRepository:
    async def test_create_submission(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=42)
        )
        assert sub.id is not None
        assert sub.test_id == test.id
        assert sub.user_id == 42

    async def test_default_status_is_assigned(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        assert sub.status == SubmissionStatus.ASSIGNED

    async def test_get_by_id_found(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        found = await TestSubmissionRepository.get_by_id(db, sub.id)
        assert found is not None
        assert found.id == sub.id

    async def test_get_by_id_not_found_returns_none(self, db):
        result = await TestSubmissionRepository.get_by_id(db, 99999)
        assert result is None

    async def test_list_all_returns_all(self, db):
        test = await _make_test(db)
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=1))
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=2))
        subs = await TestSubmissionRepository.list_all(db)
        assert len(subs) == 2

    async def test_list_by_user_filters(self, db):
        test = await _make_test(db)
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=10))
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=10))
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=99))
        subs = await TestSubmissionRepository.list_by_user(db, 10)
        assert len(subs) == 2
        assert all(s.user_id == 10 for s in subs)

    async def test_list_by_test_filters(self, db):
        t1 = await _make_test(db, "Test 1")
        t2 = await _make_test(db, "Test 2")
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=t1.id, user_id=1))
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=t1.id, user_id=2))
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=t2.id, user_id=3))
        subs = await TestSubmissionRepository.list_by_test(db, t1.id)
        assert len(subs) == 2

    async def test_get_by_user_and_test(self, db):
        test = await _make_test(db)
        await TestSubmissionRepository.create(db, TestSubmissionCreate(test_id=test.id, user_id=5))
        found = await TestSubmissionRepository.get_by_user_and_test(db, 5, test.id)
        assert found is not None
        assert found.user_id == 5
        assert found.test_id == test.id

    async def test_get_by_user_and_test_not_found(self, db):
        test = await _make_test(db)
        result = await TestSubmissionRepository.get_by_user_and_test(db, 999, test.id)
        assert result is None

    async def test_update_status(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        updated = await TestSubmissionRepository.update(
            db, sub, TestSubmissionUpdate(status=SubmissionStatus.IN_PROGRESS)
        )
        assert updated.status == SubmissionStatus.IN_PROGRESS

    async def test_update_scores(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        updated = await TestSubmissionRepository.update(
            db, sub, TestSubmissionUpdate(ai_score=82, trainer_score=88, final_score=85)
        )
        assert updated.ai_score == 82
        assert updated.trainer_score == 88
        assert updated.final_score == 85

    async def test_update_feedback(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        updated = await TestSubmissionRepository.update(
            db, sub, TestSubmissionUpdate(feedback="Great performance!")
        )
        assert updated.feedback == "Great performance!"

    async def test_delete_submission(self, db):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        sub_id = sub.id
        await TestSubmissionRepository.delete(db, sub)
        assert await TestSubmissionRepository.get_by_id(db, sub_id) is None

    @pytest.mark.parametrize("target_status", [
        SubmissionStatus.IN_PROGRESS,
        SubmissionStatus.COMPLETED,
        SubmissionStatus.EVALUATED,
        SubmissionStatus.GRADED,
        SubmissionStatus.ABANDONED,
    ])
    async def test_update_to_all_statuses(self, db, target_status):
        test = await _make_test(db)
        sub = await TestSubmissionRepository.create(
            db, TestSubmissionCreate(test_id=test.id, user_id=1)
        )
        updated = await TestSubmissionRepository.update(
            db, sub, TestSubmissionUpdate(status=target_status)
        )
        assert updated.status == target_status
