from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TrainerReviewRequest,
)

# --- SubmissionStatus enum ---


def test_submission_status_assigned_value():
    assert SubmissionStatus.ASSIGNED == "ASSIGNED"


def test_submission_status_completed_value():
    assert SubmissionStatus.COMPLETED == "COMPLETED"


def test_submission_status_invalid_raises():
    with pytest.raises(ValidationError):
        TestSubmissionCreate(test_id=1, user_id=1, status="NONEXISTENT")


# --- TestSubmissionCreate timezone stripping ---


def test_submission_create_strips_tz_from_due_date():
    dt_utc = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
    sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=dt_utc)
    assert sub.due_date is not None
    assert sub.due_date.tzinfo is None
    assert sub.due_date == datetime(2025, 6, 1, 10, 0, 0)


def test_submission_create_naive_datetime_unchanged():
    dt_naive = datetime(2025, 6, 1, 10, 0, 0)
    sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=dt_naive)
    assert sub.due_date == dt_naive
    assert sub.due_date.tzinfo is None


def test_submission_create_none_due_date_stays_none():
    sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=None)
    assert sub.due_date is None


def test_submission_create_default_status_is_assigned():
    sub = TestSubmissionCreate(test_id=1, user_id=99)
    assert sub.status == SubmissionStatus.ASSIGNED


def test_submission_create_test_id_required():
    with pytest.raises(ValidationError):
        TestSubmissionCreate(user_id=1)


def test_submission_create_user_id_required():
    with pytest.raises(ValidationError):
        TestSubmissionCreate(test_id=1)


# --- BulkAssignRequest timezone stripping ---


def test_bulk_assign_strips_tz_from_due_date():
    dt_utc = datetime(2025, 9, 1, 9, 0, 0, tzinfo=UTC)
    req = BulkAssignRequest(
        test_id=5,
        participant_emails=["a@example.com", "b@example.com"],
        due_date=dt_utc,
    )
    assert req.due_date is not None
    assert req.due_date.tzinfo is None


def test_bulk_assign_none_due_date():
    req = BulkAssignRequest(test_id=5, participant_emails=["a@example.com"])
    assert req.due_date is None


def test_bulk_assign_test_id_required():
    with pytest.raises(ValidationError):
        BulkAssignRequest(participant_emails=["a@example.com"])


# --- TrainerReviewRequest ---


def test_trainer_review_valid():
    req = TrainerReviewRequest(trainer_score=85)
    assert req.trainer_score == 85
    assert req.feedback is None
    assert req.trainer_evaluation is None


def test_trainer_review_score_required():
    with pytest.raises(ValidationError):
        TrainerReviewRequest()


def test_trainer_review_with_feedback():
    req = TrainerReviewRequest(trainer_score=70, feedback="Good work overall.")
    assert req.feedback == "Good work overall."


def test_trainer_review_with_evaluation_dict():
    req = TrainerReviewRequest(
        trainer_score=90,
        trainer_evaluation={"categories": {"docker": 95}},
    )
    assert req.trainer_evaluation is not None
    assert req.trainer_evaluation["categories"]["docker"] == 95
