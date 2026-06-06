from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from src.models.skill import Skill
from src.models.test import Test, TestType
from src.models.test_skill import TestSkill
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
)
from src.services.skill_service import SkillService
from src.services.test_service import TestService
from src.services.test_submission_service import TestSubmissionService


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def first(self):
        return self.values[0] if self.values else None

    def all(self):
        return self.values

    def scalar_one_or_none(self):
        return self.first()


class FakeResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return FakeScalarResult(self.values)

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None


class FakeDb:
    def __init__(self, values=None):
        self.values = values or []
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, statement):
        self.statement = statement
        return FakeResult(self.values)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)


def make_test(test_id=1, duration=None):
    test = Test(
        id=test_id,
        name="Java Quiz",
        test_type=TestType.QUIZ,
        role="Associate",
        curriculum="Java",
        duration=duration,
        number_of_questions=10,
        active=True,
        created_by_id=7,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return test


def make_skill(skill_id=1):
    return Skill(id=skill_id, name=f"Skill {skill_id}", description="Core skill")


def make_submission(submission_id=1, user_id=100, status=SubmissionStatus.ASSIGNED):
    now = datetime.utcnow()
    return SimpleNamespace(
        id=submission_id,
        test_id=1,
        user_id=user_id,
        assigned_by_id=7,
        due_date=None,
        status=status,
        assigned_at=now,
        started_at=None,
        submitted_at=None,
        ai_score=None,
        trainer_score=None,
        final_score=None,
        feedback=None,
        reviewed_at=None,
        reviewed_by_id=None,
        created_at=now,
        updated_at=now,
        test=None,
    )


@pytest.mark.asyncio
async def test_test_repository_get_and_list_convert_duration_seconds():
    test = make_test(duration=timedelta(minutes=30))
    db = FakeDb([test])

    found = await TestRepository.get_by_id(db, 1)
    listed = await TestRepository.list_all(db)
    by_creator = await TestRepository.list_by_creator(db, 7)

    assert found.duration_seconds == 1800
    assert listed[0].duration_seconds == 1800
    assert by_creator[0].duration_seconds == 1800


@pytest.mark.asyncio
async def test_test_repository_create_update_and_delete_mutate_db():
    db = FakeDb()
    created = await TestRepository.create(
        db,
        TestCreate(
            name="Interview",
            test_type=TestType.INTERVIEW,
            duration_seconds=900,
        ),
    )

    assert created.duration == timedelta(seconds=900)
    assert db.added == [created]
    assert db.commits == 1
    assert db.refreshed == [created]

    updated = await TestRepository.update(
        db,
        created,
        TestUpdate(name="Updated Interview", duration_seconds=1200),
    )

    assert updated.name == "Updated Interview"
    assert updated.duration == timedelta(seconds=1200)

    await TestRepository.delete(db, updated)
    assert db.deleted == [updated]


@pytest.mark.asyncio
async def test_skill_repository_crud_methods_use_async_session():
    skill = make_skill()
    db = FakeDb([skill])

    assert await SkillRepository.get_by_id(db, 1) == skill
    assert await SkillRepository.list_all(db) == [skill]

    created = await SkillRepository.create(
        db,
        SkillCreate(name="Python", description="Language"),
    )
    assert created.name == "Python"
    assert db.added[-1] == created

    updated = await SkillRepository.update(
        db,
        skill,
        SkillUpdate(description="Updated"),
    )
    assert updated.description == "Updated"

    await SkillRepository.delete(db, skill)
    assert db.deleted[-1] == skill


@pytest.mark.asyncio
async def test_test_skill_repository_crud_methods_use_async_session():
    link = TestSkill(id=1, test_id=10, skill_id=20)
    db = FakeDb([link])

    assert await TestSkillRepository.get_by_id(db, 1) == link
    assert await TestSkillRepository.list_by_test(db, 10) == [link]
    assert await TestSkillRepository.list_by_skill(db, 20) == [link]

    created = await TestSkillRepository.create(
        db,
        SimpleNamespace(dict=lambda: {"test_id": 10, "skill_id": 30}),
    )
    assert created.test_id == 10
    assert created.skill_id == 30

    await TestSkillRepository.delete(db, link)
    assert db.deleted[-1] == link


@pytest.mark.asyncio
async def test_skill_service_lists_creates_updates_and_deletes():
    db = object()
    skill = make_skill()

    with patch.object(SkillRepository, "list_all", new=AsyncMock(return_value=[skill])):
        result = await SkillService.list_skills(db)
    assert result[0].name == "Skill 1"

    with patch.object(SkillRepository, "create", new=AsyncMock(return_value=skill)):
        created = await SkillService.create_skill(
            db,
            SkillCreate(name="Skill 1", description="Core skill"),
        )
    assert created.id == 1

    with patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError):
            await SkillService.update_skill(db, 404, SkillUpdate(name="Missing"))

    with (
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
        patch.object(SkillRepository, "update", new=AsyncMock(return_value=skill)),
    ):
        updated = await SkillService.update_skill(db, 1, SkillUpdate(name="Skill 1"))
    assert updated.name == "Skill 1"

    with (
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
        patch.object(SkillRepository, "delete", new=AsyncMock()) as delete,
    ):
        await SkillService.delete_skill(db, 1)
    delete.assert_awaited_once_with(db, skill)


@pytest.mark.asyncio
async def test_test_service_create_test_links_skills_and_returns_output():
    db = object()
    test = make_test()
    skills = [make_skill(1), make_skill(2)]

    with (
        patch.object(TestRepository, "create", new=AsyncMock(return_value=test)) as create,
        patch.object(TestSkillRepository, "create", new=AsyncMock()) as create_link,
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(side_effect=skills)),
    ):
        result = await TestService.create_test(
            db,
            TestCreate(name="Java Quiz", test_type=TestType.QUIZ, skill_ids=[1, 2]),
            creator_id=7,
        )

    assert result.created_by_id == 7
    assert [skill.id for skill in result.skills] == [1, 2]
    assert create.await_args.args[1].created_by_id == 7
    assert create_link.await_count == 2


@pytest.mark.asyncio
async def test_test_service_update_handles_missing_tests_and_skill_replacement():
    db = object()
    test = make_test()
    existing_link = SimpleNamespace(skill_id=1)
    skill = make_skill(2)

    with patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError):
            await TestService.update_test(db, 404, TestUpdate(name="Missing"))

    with (
        patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=test)),
        patch.object(TestRepository, "update", new=AsyncMock(return_value=test)),
        patch.object(
            TestSkillRepository,
            "list_by_test",
            new=AsyncMock(return_value=[existing_link]),
        ),
        patch.object(TestSkillRepository, "delete", new=AsyncMock()) as delete_link,
        patch.object(TestSkillRepository, "create", new=AsyncMock()) as create_link,
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
    ):
        result = await TestService.update_test(db, 1, TestUpdate(skill_ids=[2]))

    assert result.skills[0].id == 2
    delete_link.assert_awaited_once_with(db, existing_link)
    create_link.assert_awaited_once()


@pytest.mark.asyncio
async def test_test_service_read_list_and_delete_paths():
    db = object()
    test = make_test()
    skill = make_skill()
    link = SimpleNamespace(skill_id=1)

    with patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError):
            await TestService.get_test_by_id(db, 404)

    with (
        patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=test)),
        patch.object(TestSkillRepository, "list_by_test", new=AsyncMock(return_value=[link])),
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
    ):
        result = await TestService.get_test_by_id(db, 1)
    assert result.skills[0].name == "Skill 1"

    with (
        patch.object(TestRepository, "list_all", new=AsyncMock(return_value=[test])),
        patch.object(TestSkillRepository, "list_by_test", new=AsyncMock(return_value=[link])),
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
    ):
        assert len(await TestService.list_all_tests(db)) == 1

    with (
        patch.object(TestRepository, "list_by_creator", new=AsyncMock(return_value=[test])),
        patch.object(TestSkillRepository, "list_by_test", new=AsyncMock(return_value=[link])),
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
    ):
        assert len(await TestService.list_tests_created_by_user(db, 7)) == 1

    with (
        patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=test)),
        patch.object(TestRepository, "delete", new=AsyncMock()) as delete,
    ):
        await TestService.delete_test(db, 1)
    delete.assert_awaited_once_with(db, test)


@pytest.mark.asyncio
async def test_test_service_lists_tests_with_submissions_by_user():
    db = object()
    test = make_test()
    skill = make_skill()
    link = SimpleNamespace(skill_id=1)
    submission = SimpleNamespace(test_id=1)

    with (
        patch(
            "src.repositories.test_submission_repository.TestSubmissionRepository.list_by_user",
            new=AsyncMock(return_value=[submission, submission]),
        ),
        patch.object(TestRepository, "get_by_id", new=AsyncMock(return_value=test)),
        patch.object(TestSkillRepository, "list_by_test", new=AsyncMock(return_value=[link])),
        patch.object(SkillRepository, "get_by_id", new=AsyncMock(return_value=skill)),
    ):
        result = await TestService.list_tests_with_submissions_by_user(db, 99)

    assert len(result) == 1
    assert result[0].skills[0].id == 1


@pytest.mark.asyncio
async def test_submission_service_crud_and_list_paths():
    db = object()
    submission = make_submission()

    with patch.object(
        TestSubmissionRepository,
        "create",
        new=AsyncMock(return_value=submission),
    ) as create:
        created = await TestSubmissionService.create_submission(
            db,
            TestSubmissionCreate(test_id=1, user_id=100, assigned_by_id=7),
        )
    assert created.id == 1
    create.assert_awaited_once()

    with patch.object(
        TestSubmissionRepository,
        "get_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ValueError):
            await TestSubmissionService.update_submission(
                db,
                404,
                TestSubmissionUpdate(status=SubmissionStatus.IN_PROGRESS),
            )

    with (
        patch.object(
            TestSubmissionRepository,
            "get_by_id",
            new=AsyncMock(return_value=submission),
        ),
        patch.object(
            TestSubmissionRepository,
            "update",
            new=AsyncMock(return_value=make_submission(status=SubmissionStatus.IN_PROGRESS)),
        ) as update,
    ):
        updated = await TestSubmissionService.update_submission(
            db,
            1,
            TestSubmissionUpdate(status=SubmissionStatus.IN_PROGRESS),
        )
    assert updated.status == SubmissionStatus.IN_PROGRESS
    update.assert_awaited_once()

    with patch.object(
        TestSubmissionRepository,
        "get_by_id",
        new=AsyncMock(return_value=submission),
    ):
        found = await TestSubmissionService.get_submission_by_id(db, 1)
    assert found.user_id == 100

    with patch.object(
        TestSubmissionRepository,
        "get_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ValueError):
            await TestSubmissionService.get_submission_by_id(db, 404)

    with patch.object(
        TestSubmissionRepository,
        "get_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ValueError):
            await TestSubmissionService.delete_submission(db, 404)

    with (
        patch.object(
            TestSubmissionRepository,
            "get_by_id",
            new=AsyncMock(return_value=submission),
        ),
        patch.object(TestSubmissionRepository, "delete", new=AsyncMock()) as delete,
    ):
        await TestSubmissionService.delete_submission(db, 1)
    delete.assert_awaited_once_with(db, submission)

    with patch.object(
        TestSubmissionRepository,
        "list_all",
        new=AsyncMock(return_value=[submission]),
    ):
        assert len(await TestSubmissionService.list_all_submissions(db)) == 1

    with patch.object(
        TestSubmissionRepository,
        "list_by_user",
        new=AsyncMock(return_value=[submission]),
    ):
        assert len(await TestSubmissionService.list_submissions_by_user(db, 100)) == 1


@pytest.mark.asyncio
async def test_bulk_assign_test_handles_existing_invited_and_failed_users():
    db = object()
    request = BulkAssignRequest(
        test_id=1,
        participant_emails=[
            "existing@example.com",
            "new@example.com",
            "bad@example.com",
        ],
    )

    class FakeResponse:
        def __init__(self, status_code, payload=None, text=""):
            self.status_code = status_code
            self.payload = payload or {}
            self.text = text

        def json(self):
            return self.payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            if "existing@example.com" in url:
                return FakeResponse(200, {"id": 101})
            if "new@example.com" in url:
                return FakeResponse(404)
            return FakeResponse(500, text="user-service error")

        async def post(self, url, json):
            return FakeResponse(201, {"id": 202})

    created_submissions = [
        make_submission(1, user_id=101),
        make_submission(2, user_id=202),
    ]

    with (
        patch.object(TestService, "get_test_by_id", new=AsyncMock(return_value=make_test())),
        patch(
            "src.services.test_submission_service.httpx.AsyncClient",
            return_value=FakeClient(),
        ),
        patch.object(
            TestSubmissionRepository,
            "create",
            new=AsyncMock(side_effect=created_submissions),
        ) as create,
    ):
        result = await TestSubmissionService.bulk_assign_test(
            db,
            request,
            current_user={"id": 7},
        )

    assert result.success_count == 2
    assert result.failure_count == 1
    assert [submission.user_id for submission in result.created_submissions] == [101, 202]
    assert result.errors[0]["email"] == "bad@example.com"
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_bulk_assign_test_requires_existing_test():
    with patch.object(TestService, "get_test_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError):
            await TestSubmissionService.bulk_assign_test(
                object(),
                BulkAssignRequest(test_id=404, participant_emails=["user@example.com"]),
                current_user={"id": 7},
            )
