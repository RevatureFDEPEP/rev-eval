from datetime import datetime, timezone

import pytest
from src.models.test import TestType
from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TrainerReviewRequest,
)


class TestTestCreateSchema:
    @pytest.mark.parametrize("name,test_type,duration", [
        ("Java Quiz", TestType.QUIZ, 2700),
        ("Python Interview", TestType.INTERVIEW, None),
        ("Spring Boot Test", TestType.QUIZ, 3600),
        ("Data Science Quiz", TestType.QUIZ, 1800),
    ])
    def test_valid_test_create(self, name, test_type, duration):
        data = TestCreate(name=name, test_type=test_type, duration_seconds=duration)
        assert data.name == name
        assert data.test_type == test_type
        assert data.duration_seconds == duration

    def test_skill_ids_default_empty_list(self):
        tc = TestCreate(name="Test", test_type=TestType.QUIZ)
        assert tc.skill_ids == []

    def test_number_of_questions_defaults_20(self):
        tc = TestCreate(name="Test", test_type=TestType.QUIZ)
        assert tc.number_of_questions == 20

    def test_active_defaults_true(self):
        tc = TestCreate(name="Test", test_type=TestType.QUIZ)
        assert tc.active is True

    @pytest.mark.parametrize("test_type", ["QUIZ", "INTERVIEW"])
    def test_test_type_string_coercion(self, test_type):
        tc = TestCreate(name="Test", test_type=test_type)
        assert tc.test_type == test_type

    def test_skill_ids_accepted(self):
        tc = TestCreate(name="Test", test_type=TestType.QUIZ, skill_ids=[1, 2, 3])
        assert tc.skill_ids == [1, 2, 3]


class TestTestUpdateSchema:
    def test_all_fields_optional(self):
        update = TestUpdate()
        assert update.name is None
        assert update.test_type is None
        assert update.active is None

    @pytest.mark.parametrize("field,value", [
        ("name", "Updated Name"),
        ("active", False),
        ("number_of_questions", 30),
        ("role", "Senior Dev"),
    ])
    def test_partial_update(self, field, value):
        update = TestUpdate(**{field: value})
        assert getattr(update, field) == value


class TestSkillSchemas:
    @pytest.mark.parametrize("name,desc", [
        ("Python", "Python programming language"),
        ("Java", None),
        ("SQL", "Structured Query Language"),
    ])
    def test_valid_skill_create(self, name, desc):
        skill = SkillCreate(name=name, description=desc)
        assert skill.name == name
        assert skill.description == desc

    def test_skill_update_all_optional(self):
        update = SkillUpdate()
        assert update.name is None
        assert update.description is None

    @pytest.mark.parametrize("field,value", [
        ("name", "Renamed Skill"),
        ("description", "New description text"),
    ])
    def test_skill_update_partial(self, field, value):
        update = SkillUpdate(**{field: value})
        assert getattr(update, field) == value


class TestSubmissionCreateSchema:
    def test_valid_submission(self):
        sub = TestSubmissionCreate(test_id=1, user_id=42)
        assert sub.test_id == 1
        assert sub.user_id == 42
        assert sub.status == SubmissionStatus.ASSIGNED

    def test_timezone_stripped_from_due_date(self):
        aware_dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        sub = TestSubmissionCreate(test_id=1, user_id=1, due_date=aware_dt)
        assert sub.due_date is not None
        assert sub.due_date.tzinfo is None

    def test_naive_due_date_unchanged(self):
        naive_dt = datetime(2025, 6, 15, 12, 0, 0)
        sub = TestSubmissionCreate(test_id=1, user_id=1, due_date=naive_dt)
        assert sub.due_date == naive_dt

    def test_due_date_optional(self):
        sub = TestSubmissionCreate(test_id=1, user_id=1)
        assert sub.due_date is None


class TestSubmissionUpdateSchema:
    @pytest.mark.parametrize("status", list(SubmissionStatus))
    def test_all_statuses_accepted(self, status):
        update = TestSubmissionUpdate(status=status)
        assert update.status == status

    def test_all_fields_optional(self):
        update = TestSubmissionUpdate()
        assert update.status is None
        assert update.ai_score is None
        assert update.trainer_score is None
        assert update.final_score is None
        assert update.feedback is None

    @pytest.mark.parametrize("score", [0, 50, 100])
    def test_score_values(self, score):
        update = TestSubmissionUpdate(ai_score=score, trainer_score=score, final_score=score)
        assert update.ai_score == score

    def test_timezone_stripped_from_started_at(self):
        aware_dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        update = TestSubmissionUpdate(started_at=aware_dt)
        assert update.started_at.tzinfo is None

    def test_timezone_stripped_from_submitted_at(self):
        aware_dt = datetime(2025, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        update = TestSubmissionUpdate(submitted_at=aware_dt)
        assert update.submitted_at.tzinfo is None


class TestBulkAssignRequest:
    def test_valid_bulk_assign(self):
        req = BulkAssignRequest(test_id=1, participant_emails=["a@test.com", "b@test.com"])
        assert req.test_id == 1
        assert len(req.participant_emails) == 2

    def test_timezone_stripped_from_due_date(self):
        aware_dt = datetime(2025, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
        req = BulkAssignRequest(test_id=1, participant_emails=["x@t.com"], due_date=aware_dt)
        assert req.due_date.tzinfo is None

    def test_due_date_optional(self):
        req = BulkAssignRequest(test_id=1, participant_emails=["a@b.com"])
        assert req.due_date is None


class TestTrainerReviewRequest:
    @pytest.mark.parametrize("score", [0, 50, 75, 100])
    def test_valid_scores(self, score):
        req = TrainerReviewRequest(trainer_score=score)
        assert req.trainer_score == score

    def test_feedback_optional(self):
        req = TrainerReviewRequest(trainer_score=85)
        assert req.feedback is None

    def test_feedback_accepted(self):
        req = TrainerReviewRequest(trainer_score=90, feedback="Excellent work!")
        assert req.feedback == "Excellent work!"
