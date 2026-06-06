"""Repository-layer tests against an in-memory async SQLite session.

These cover the runtime data transformations that happen *after* Pydantic
validation — duration_seconds <-> timedelta conversion, timezone stripping,
filtering/ordering — where schema tests can't reach.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.test import TestType
from src.models.test_submission import TestSubmission
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate
from src.schemas.test_skill_schema import TestSkillCreate
from src.schemas.test_submission_schema import (
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
)

# ===== TestRepository =====


@pytest.mark.asyncio
class TestTestRepository:
    async def test_create_converts_duration_seconds_to_timedelta(self, db_session):
        test = await TestRepository.create(
            db_session,
            TestCreate(name="Quiz A", test_type=TestType.QUIZ, duration_seconds=3600),
        )
        assert test.id is not None
        assert test.duration == timedelta(hours=1)

    async def test_create_without_duration_stores_none(self, db_session):
        test = await TestRepository.create(
            db_session, TestCreate(name="No timer", test_type=TestType.INTERVIEW)
        )
        assert test.duration is None

    async def test_get_by_id_round_trips_duration_seconds(self, db_session):
        created = await TestRepository.create(
            db_session,
            TestCreate(name="Quiz B", test_type=TestType.QUIZ, duration_seconds=5400),
        )
        fetched = await TestRepository.get_by_id(db_session, created.id)
        assert fetched.duration_seconds == 5400

    async def test_get_by_id_missing_returns_none(self, db_session):
        # Regression: used to raise AttributeError assigning duration_seconds on None
        assert await TestRepository.get_by_id(db_session, 99999) is None

    async def test_update_converts_duration_seconds(self, db_session):
        test = await TestRepository.create(
            db_session,
            TestCreate(name="Quiz C", test_type=TestType.QUIZ, duration_seconds=600),
        )
        updated = await TestRepository.update(
            db_session, test, TestUpdate(duration_seconds=1200)
        )
        assert updated.duration == timedelta(minutes=20)

    async def test_update_partial_keeps_other_fields(self, db_session):
        test = await TestRepository.create(
            db_session,
            TestCreate(name="Original", test_type=TestType.QUIZ, role="QA"),
        )
        updated = await TestRepository.update(
            db_session, test, TestUpdate(name="Renamed")
        )
        assert updated.name == "Renamed"
        assert updated.role == "QA"

    async def test_list_by_creator_filters_and_orders_desc(self, db_session):
        for name, creator, created_at in [
            ("Old", 1, datetime(2026, 1, 1)),
            ("New", 1, datetime(2026, 2, 1)),
            ("Other", 2, datetime(2026, 3, 1)),
        ]:
            test = await TestRepository.create(
                db_session,
                TestCreate(name=name, test_type=TestType.QUIZ, created_by_id=creator),
            )
            # Pin created_at so ordering is deterministic
            test.created_at = created_at
            await db_session.commit()

        tests = await TestRepository.list_by_creator(db_session, creator_id=1)
        assert [t.name for t in tests] == ["New", "Old"]

    async def test_delete_removes_row(self, db_session):
        test = await TestRepository.create(
            db_session, TestCreate(name="Doomed", test_type=TestType.QUIZ)
        )
        await TestRepository.delete(db_session, test)
        assert await TestRepository.get_by_id(db_session, test.id) is None


# ===== TestSubmissionRepository =====

AWARE = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
NAIVE = datetime(2026, 6, 1, 12, 0)


class TestSubmissionRepositoryHelpers:
    def test_strip_timezone_converts_aware_fields(self):
        data = {
            "due_date": AWARE,
            "assigned_at": AWARE,
            "started_at": AWARE,
            "submitted_at": AWARE,
        }
        stripped = TestSubmissionRepository._strip_timezone_from_dict(data)
        for field in ("due_date", "assigned_at", "started_at", "submitted_at"):
            assert stripped[field].tzinfo is None
            assert stripped[field] == NAIVE

    def test_strip_timezone_leaves_naive_and_none_untouched(self):
        data = {"due_date": NAIVE, "started_at": None, "feedback": "not a datetime"}
        stripped = TestSubmissionRepository._strip_timezone_from_dict(data)
        assert stripped["due_date"] == NAIVE
        assert stripped["started_at"] is None
        assert stripped["feedback"] == "not a datetime"


@pytest.mark.asyncio
class TestTestSubmissionRepository:
    async def _make_test(self, db_session):
        return await TestRepository.create(
            db_session, TestCreate(name="Host test", test_type=TestType.QUIZ)
        )

    async def test_create_persists_naive_due_date(self, db_session):
        test = await self._make_test(db_session)
        submission = await TestSubmissionRepository.create(
            db_session,
            TestSubmissionCreate(test_id=test.id, user_id=7, due_date=AWARE),
        )
        assert submission.due_date.tzinfo is None
        assert submission.status == SubmissionStatus.ASSIGNED

    async def test_update_applies_fields_and_strips_timezone(self, db_session):
        test = await self._make_test(db_session)
        submission = await TestSubmissionRepository.create(
            db_session, TestSubmissionCreate(test_id=test.id, user_id=7)
        )
        updated = await TestSubmissionRepository.update(
            db_session,
            submission,
            TestSubmissionUpdate(
                status=SubmissionStatus.COMPLETED,
                submitted_at=AWARE,
                final_score=88,
            ),
        )
        assert updated.status == SubmissionStatus.COMPLETED
        assert updated.submitted_at == NAIVE
        assert updated.submitted_at.tzinfo is None
        assert updated.final_score == 88

    async def test_get_by_user_and_test_returns_most_recent(self, db_session):
        test = await self._make_test(db_session)
        old = TestSubmission(
            test_id=test.id, user_id=7, created_at=datetime(2026, 1, 1)
        )
        new = TestSubmission(
            test_id=test.id, user_id=7, created_at=datetime(2026, 2, 1), final_score=90
        )
        db_session.add_all([old, new])
        await db_session.commit()

        found = await TestSubmissionRepository.get_by_user_and_test(
            db_session, user_id=7, test_id=test.id
        )
        assert found.final_score == 90

    async def test_list_by_user_filters(self, db_session):
        test = await self._make_test(db_session)
        db_session.add_all(
            [
                TestSubmission(
                    test_id=test.id, user_id=7, created_at=datetime(2026, 1, 1)
                ),
                TestSubmission(
                    test_id=test.id, user_id=8, created_at=datetime(2026, 1, 2)
                ),
            ]
        )
        await db_session.commit()

        mine = await TestSubmissionRepository.list_by_user(db_session, user_id=7)
        assert len(mine) == 1
        assert mine[0].user_id == 7

    async def test_delete_removes_submission(self, db_session):
        test = await self._make_test(db_session)
        submission = await TestSubmissionRepository.create(
            db_session, TestSubmissionCreate(test_id=test.id, user_id=7)
        )
        await TestSubmissionRepository.delete(db_session, submission)
        assert (
            await TestSubmissionRepository.get_by_id(db_session, submission.id) is None
        )


# ===== SkillRepository =====


@pytest.mark.asyncio
class TestSkillRepositoryCrud:
    async def test_create_and_get_by_id(self, db_session):
        skill = await SkillRepository.create(
            db_session, SkillCreate(name="Python", description="Core language")
        )
        fetched = await SkillRepository.get_by_id(db_session, skill.id)
        assert fetched.name == "Python"

    async def test_update_partial_preserves_description(self, db_session):
        skill = await SkillRepository.create(
            db_session, SkillCreate(name="SQL", description="Joins and indexes")
        )
        updated = await SkillRepository.update(
            db_session, skill, SkillUpdate(name="SQL 2")
        )
        assert updated.name == "SQL 2"
        assert updated.description == "Joins and indexes"

    async def test_list_all_ordered_by_id(self, db_session):
        for name in ("B", "A", "C"):
            await SkillRepository.create(db_session, SkillCreate(name=name))
        skills = await SkillRepository.list_all(db_session)
        assert [s.name for s in skills] == ["B", "A", "C"]

    async def test_delete(self, db_session):
        skill = await SkillRepository.create(db_session, SkillCreate(name="Doomed"))
        await SkillRepository.delete(db_session, skill)
        assert await SkillRepository.get_by_id(db_session, skill.id) is None


# ===== TestSkillRepository =====


@pytest.mark.asyncio
class TestTestSkillRepositoryCrud:
    async def test_create_and_list_by_test(self, db_session):
        test = await TestRepository.create(
            db_session, TestCreate(name="Linked", test_type=TestType.QUIZ)
        )
        skill = await SkillRepository.create(db_session, SkillCreate(name="Docker"))
        link = await TestSkillRepository.create(
            db_session, TestSkillCreate(test_id=test.id, skill_id=skill.id)
        )
        assert link.id is not None

        links = await TestSkillRepository.list_by_test(db_session, test.id)
        assert len(links) == 1
        assert links[0].skill_id == skill.id

    async def test_list_by_skill_filters(self, db_session):
        test = await TestRepository.create(
            db_session, TestCreate(name="T", test_type=TestType.QUIZ)
        )
        s1 = await SkillRepository.create(db_session, SkillCreate(name="K8s"))
        s2 = await SkillRepository.create(db_session, SkillCreate(name="Git"))
        await TestSkillRepository.create(
            db_session, TestSkillCreate(test_id=test.id, skill_id=s1.id)
        )
        await TestSkillRepository.create(
            db_session, TestSkillCreate(test_id=test.id, skill_id=s2.id)
        )

        only_s1 = await TestSkillRepository.list_by_skill(db_session, s1.id)
        assert len(only_s1) == 1
        assert only_s1[0].test_id == test.id
