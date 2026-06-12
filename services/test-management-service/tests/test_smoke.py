"""
Smoke tests for test-management-service — no database required.

Covers: Pydantic schema validation for Test, TestSubmission, Skill, and
BulkAssign payloads including parameterized timezone-stripping assertions.
"""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from src.schemas.skill_schema import SkillCreate, SkillOut, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TrainerReviewRequest,
)

# ── TestCreate / TestUpdate ───────────────────────────────────────────────────

def test_test_create_applies_default_values():
    tc = TestCreate(name="Java Fundamentals Quiz", test_type="QUIZ")
    assert tc.name == "Java Fundamentals Quiz"
    assert tc.test_type.value == "QUIZ"
    assert tc.number_of_questions == 20
    assert tc.active is True
    assert tc.skill_ids == []


def test_test_create_accepts_interview_type():
    tc = TestCreate(name="System Design Interview", test_type="INTERVIEW")
    assert tc.test_type.value == "INTERVIEW"


def test_test_update_allows_partial_payload():
    tu = TestUpdate(active=False)
    assert tu.active is False
    assert tu.name is None
    assert tu.test_type is None


# ── SkillCreate / SkillUpdate / SkillOut ──────────────────────────────────────

def test_skill_create_accepts_name_and_description():
    sc = SkillCreate(name="Spring Boot", description="Backend framework skill")
    assert sc.name == "Spring Boot"
    assert sc.description == "Backend framework skill"


def test_skill_create_requires_name():
    with pytest.raises(ValidationError):
        SkillCreate()


def test_skill_update_allows_all_fields_optional():
    su = SkillUpdate()
    assert su.name is None
    assert su.description is None


def test_skill_out_reads_from_orm_attributes():
    class FakeRow:
        id = 5
        name = "PostgreSQL"
        description = "Relational database"

    out = SkillOut.model_validate(FakeRow())
    assert out.id == 5
    assert out.name == "PostgreSQL"


# ── TestSubmissionCreate ──────────────────────────────────────────────────────

def test_submission_create_defaults_to_assigned_status():
    sub = TestSubmissionCreate(test_id=1, user_id=100)
    assert sub.status == SubmissionStatus.ASSIGNED


@pytest.mark.parametrize("tz", [
    timezone.utc,
    timezone(timedelta(hours=-5)),
    timezone(timedelta(hours=5, minutes=30)),
])
def test_submission_create_strips_timezone_from_due_date(tz):
    due = datetime(2026, 8, 1, 12, 0, tzinfo=tz)
    sub = TestSubmissionCreate(test_id=1, user_id=100, due_date=due)
    assert sub.due_date is not None
    assert sub.due_date.tzinfo is None


# ── TestSubmissionUpdate ──────────────────────────────────────────────────────

def test_submission_update_strips_timezone_from_datetime_fields():
    submitted = datetime(2026, 6, 3, 13, 45, tzinfo=timezone.utc)
    update = TestSubmissionUpdate(submitted_at=submitted)
    assert update.submitted_at.tzinfo is None


# ── BulkAssignRequest ─────────────────────────────────────────────────────────

def test_bulk_assign_strips_timezone_from_due_date():
    due = datetime(2026, 6, 3, 17, 0, tzinfo=timezone.utc)
    req = BulkAssignRequest(
        test_id=1,
        participant_emails=["a@example.com", "b@example.com"],
        due_date=due,
    )
    assert req.due_date.tzinfo is None
    assert len(req.participant_emails) == 2


# ── TrainerReviewRequest ──────────────────────────────────────────────────────

def test_trainer_review_request_accepts_score_and_evaluation():
    review = TrainerReviewRequest(
        trainer_score=88,
        feedback="Good technical depth.",
        trainer_evaluation={"communication": "clear"},
    )
    assert review.trainer_score == 88
    assert review.trainer_evaluation["communication"] == "clear"
