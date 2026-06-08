"""Service-layer tests using the real in-memory async session.

Services orchestrate repositories, so these run against the same aiosqlite
fixture as the repository tests — only cross-service HTTP (user-service) is
mocked, via httpx.AsyncClient patched at the service module boundary.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.test import TestType
from src.repositories.test_skill_repository import TestSkillRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TrainerReviewRequest,
)
from src.services.skill_service import SkillService
from src.services.test_service import TestService
from src.services.test_submission_service import TestSubmissionService

# ===== HTTP mock helpers =====


def make_response(status_code: int, payload: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = text
    return response


def mock_async_client(get_side_effect=None, post_side_effect=None):
    """Build an httpx.AsyncClient stand-in usable as `async with client() as c`."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=get_side_effect)
    client.post = AsyncMock(side_effect=post_side_effect)
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=client)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    return context_manager


HTTPX_CLIENT = "src.services.test_submission_service.httpx.AsyncClient"


# ===== TestService =====


@pytest.mark.asyncio
class TestTestService:
    async def test_create_test_links_skills(self, db_session):
        skill = await SkillService.create_skill(db_session, SkillCreate(name="Python"))
        out = await TestService.create_test(
            db_session,
            TestCreate(name="Quiz", test_type=TestType.QUIZ, skill_ids=[skill.id]),
            creator_id=1,
        )
        assert [s.name for s in out.skills] == ["Python"]
        links = await TestSkillRepository.list_by_test(db_session, out.id)
        assert len(links) == 1

    async def test_create_test_sets_creator_id(self, db_session):
        out = await TestService.create_test(
            db_session,
            TestCreate(name="Quiz", test_type=TestType.QUIZ, created_by_id=999),
            creator_id=42,
        )
        assert out.created_by_id == 42  # creator arg wins over payload

    async def test_update_test_replaces_skill_links(self, db_session):
        s1 = await SkillService.create_skill(db_session, SkillCreate(name="SQL"))
        s2 = await SkillService.create_skill(db_session, SkillCreate(name="Docker"))
        created = await TestService.create_test(
            db_session,
            TestCreate(name="Quiz", test_type=TestType.QUIZ, skill_ids=[s1.id]),
            creator_id=1,
        )

        out = await TestService.update_test(
            db_session, created.id, TestUpdate(skill_ids=[s2.id])
        )
        assert [s.name for s in out.skills] == ["Docker"]
        links = await TestSkillRepository.list_by_test(db_session, created.id)
        assert [link.skill_id for link in links] == [s2.id]

    async def test_update_test_without_skill_ids_keeps_links(self, db_session):
        skill = await SkillService.create_skill(db_session, SkillCreate(name="K8s"))
        created = await TestService.create_test(
            db_session,
            TestCreate(name="Quiz", test_type=TestType.QUIZ, skill_ids=[skill.id]),
            creator_id=1,
        )

        out = await TestService.update_test(
            db_session, created.id, TestUpdate(name="Renamed")
        )
        assert out.name == "Renamed"
        assert [s.name for s in out.skills] == ["K8s"]

    async def test_get_test_by_id_missing_raises(self, db_session):
        with pytest.raises(ValueError, match="Test not found"):
            await TestService.get_test_by_id(db_session, 99999)

    async def test_delete_test_missing_raises(self, db_session):
        with pytest.raises(ValueError, match="Test not found"):
            await TestService.delete_test(db_session, 99999)

    async def test_list_tests_with_submissions_by_user_dedupes(self, db_session):
        created = await TestService.create_test(
            db_session, TestCreate(name="Quiz", test_type=TestType.QUIZ), creator_id=1
        )
        for _ in range(2):  # two submissions, same test
            await TestSubmissionRepository.create(
                db_session, TestSubmissionCreate(test_id=created.id, user_id=7)
            )

        tests = await TestService.list_tests_with_submissions_by_user(db_session, 7)
        assert [t.id for t in tests] == [created.id]


# ===== SkillService =====


@pytest.mark.asyncio
class TestSkillService:
    async def test_update_skill_partial(self, db_session):
        skill = await SkillService.create_skill(
            db_session, SkillCreate(name="Git", description="VCS")
        )
        out = await SkillService.update_skill(
            db_session, skill.id, SkillUpdate(name="Git 2")
        )
        assert out.name == "Git 2"
        assert out.description == "VCS"

    async def test_update_skill_missing_raises(self, db_session):
        with pytest.raises(ValueError, match="Skill not found"):
            await SkillService.update_skill(db_session, 99999, SkillUpdate(name="X"))

    async def test_delete_skill_missing_raises(self, db_session):
        with pytest.raises(ValueError, match="Skill not found"):
            await SkillService.delete_skill(db_session, 99999)


# ===== TestSubmissionService =====


@pytest.mark.asyncio
class TestTestSubmissionService:
    async def _make_test(self, db_session):
        return await TestService.create_test(
            db_session, TestCreate(name="Host", test_type=TestType.QUIZ), creator_id=1
        )

    async def _make_submission(self, db_session, test_id, status=None, **kwargs):
        submission = await TestSubmissionRepository.create(
            db_session, TestSubmissionCreate(test_id=test_id, user_id=7, **kwargs)
        )
        if status is not None:
            submission.status = status
            await db_session.commit()
        return submission

    async def test_create_submission_defaults_to_assigned(self, db_session):
        test = await self._make_test(db_session)
        out = await TestSubmissionService.create_submission(
            db_session, TestSubmissionCreate(test_id=test.id, user_id=7)
        )
        assert out.status == SubmissionStatus.ASSIGNED

    async def test_update_submission_missing_raises(self, db_session):
        with pytest.raises(ValueError, match="Submission not found"):
            await TestSubmissionService.update_submission(
                db_session, 99999, TestSubmissionUpdate(final_score=1)
            )

    async def test_submit_trainer_review_grades_evaluated_submission(self, db_session):
        test = await self._make_test(db_session)
        submission = await self._make_submission(
            db_session, test.id, status=SubmissionStatus.EVALUATED
        )

        response = await TestSubmissionService.submit_trainer_review(
            db_session,
            submission.id,
            TrainerReviewRequest(trainer_score=85, feedback="solid"),
            trainer_id=42,
        )

        assert response.status == SubmissionStatus.GRADED
        assert response.trainer_score == 85
        assert response.final_score == 85  # trainer score is authoritative
        assert response.reviewed_by_id == 42
        assert response.reviewed_at is not None

    async def test_submit_trainer_review_rejects_non_evaluated(self, db_session):
        test = await self._make_test(db_session)
        submission = await self._make_submission(db_session, test.id)  # ASSIGNED

        with pytest.raises(ValueError, match="not in EVALUATED status"):
            await TestSubmissionService.submit_trainer_review(
                db_session,
                submission.id,
                TrainerReviewRequest(trainer_score=85),
                trainer_id=42,
            )

    async def test_bulk_assign_missing_test_raises(self, db_session):
        with pytest.raises(ValueError, match="Test not found"):
            await TestSubmissionService.bulk_assign_test(
                db_session,
                BulkAssignRequest(test_id=99999, participant_emails=["a@x.com"]),
                current_user={"id": 1},
            )

    async def test_bulk_assign_mixed_outcomes(self, db_session):
        test = await self._make_test(db_session)

        def fake_get(url):
            if "by-email/exists@x.com" in url:
                return make_response(200, {"id": 11})
            if "by-email/new@x.com" in url:
                return make_response(404)
            return make_response(500, text="user service exploded")

        def fake_post(url, json=None):
            return make_response(201, {"id": 22})

        with patch(HTTPX_CLIENT, return_value=mock_async_client(fake_get, fake_post)):
            result = await TestSubmissionService.bulk_assign_test(
                db_session,
                BulkAssignRequest(
                    test_id=test.id,
                    participant_emails=["exists@x.com", "new@x.com", "bad@x.com"],
                ),
                current_user={"id": 1},
            )

        assert result.success_count == 2
        assert result.failure_count == 1
        assert {s.user_id for s in result.created_submissions} == {11, 22}
        assert result.errors[0]["email"] == "bad@x.com"

        persisted = await TestSubmissionRepository.list_by_test(db_session, test.id)
        assert len(persisted) == 2
        assert all(s.status == SubmissionStatus.ASSIGNED for s in persisted)

    async def test_get_evaluated_submissions_filters_and_names(self, db_session):
        test = await self._make_test(db_session)
        evaluated = await self._make_submission(
            db_session, test.id, status=SubmissionStatus.EVALUATED
        )
        evaluated.submitted_at = datetime(2026, 1, 1)
        await self._make_submission(db_session, test.id, status=SubmissionStatus.GRADED)
        await db_session.commit()

        def fake_get(url):
            return make_response(
                200,
                {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@x.com"},
            )

        with patch(HTTPX_CLIENT, return_value=mock_async_client(fake_get)):
            results = await TestSubmissionService.get_evaluated_submissions_for_trainer(
                db_session, trainer_id=1
            )

        assert [r.id for r in results] == [evaluated.id]  # GRADED one excluded
        assert results[0].participant_name == "Ada Lovelace"
        assert results[0].participant_email == "ada@x.com"

    async def test_get_evaluated_submissions_name_fallback_on_error(self, db_session):
        test = await self._make_test(db_session)
        submission = await self._make_submission(
            db_session, test.id, status=SubmissionStatus.EVALUATED
        )
        submission.submitted_at = datetime(2026, 1, 1)
        await db_session.commit()

        def fake_get(url):
            raise RuntimeError("user service down")

        with patch(HTTPX_CLIENT, return_value=mock_async_client(fake_get)):
            results = await TestSubmissionService.get_evaluated_submissions_for_trainer(
                db_session, trainer_id=1
            )

        assert results[0].participant_name == f"User #{submission.user_id}"
