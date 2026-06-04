from datetime import datetime, timezone

from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate as TestCreateSchema
from src.schemas.test_schema import TestUpdate as TestUpdateSchema
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate as TestSubmissionCreateSchema,
    TestSubmissionUpdate as TestSubmissionUpdateSchema,
    TrainerReviewRequest,
)


def test_test_create_applies_default_values():
    test_create = TestCreateSchema(
        name="Java Fundamentals Quiz",
        test_type="QUIZ",
    )

    assert test_create.name == "Java Fundamentals Quiz"
    assert test_create.test_type.value == "QUIZ"
    assert test_create.number_of_questions == 20
    assert test_create.active is True
    assert test_create.skill_ids == []


def test_test_update_allows_partial_payload():
    test_update = TestUpdateSchema(active=False)

    assert test_update.active is False
    assert test_update.name is None
    assert test_update.test_type is None


def test_skill_create_accepts_name_and_description():
    skill_create = SkillCreate(
        name="Spring Boot",
        description="Backend framework skill",
    )

    assert skill_create.name == "Spring Boot"
    assert skill_create.description == "Backend framework skill"


def test_skill_update_allows_partial_description_update():
    skill_update = SkillUpdate(description="Updated skill description")

    assert skill_update.name is None
    assert skill_update.description == "Updated skill description"


def test_submission_create_defaults_to_assigned_status():
    submission = TestSubmissionCreateSchema(
        test_id=1,
        user_id=100,
    )

    assert submission.test_id == 1
    assert submission.user_id == 100
    assert submission.status == SubmissionStatus.ASSIGNED


def test_submission_create_strips_timezone_from_due_date():
    due_date = datetime(2026, 6, 3, 12, 30, tzinfo=timezone.utc)

    submission = TestSubmissionCreateSchema(
        test_id=1,
        user_id=100,
        due_date=due_date,
    )

    assert submission.due_date.tzinfo is None


def test_submission_update_strips_timezone_from_datetime_fields():
    submitted_at = datetime(2026, 6, 3, 13, 45, tzinfo=timezone.utc)

    submission_update = TestSubmissionUpdateSchema(submitted_at=submitted_at)

    assert submission_update.submitted_at.tzinfo is None


def test_bulk_assign_request_strips_timezone_from_due_date():
    due_date = datetime(2026, 6, 3, 17, 0, tzinfo=timezone.utc)

    request = BulkAssignRequest(
        test_id=1,
        participant_emails=["participant@example.com"],
        due_date=due_date,
    )

    assert request.due_date.tzinfo is None
    assert request.participant_emails == ["participant@example.com"]


def test_trainer_review_request_accepts_score_and_evaluation_payload():
    review = TrainerReviewRequest(
        trainer_score=92,
        feedback="Strong technical reasoning.",
        trainer_evaluation={"communication": "clear", "technical_depth": "strong"},
    )

    assert review.trainer_score == 92
    assert review.feedback == "Strong technical reasoning."
    assert review.trainer_evaluation["technical_depth"] == "strong"
