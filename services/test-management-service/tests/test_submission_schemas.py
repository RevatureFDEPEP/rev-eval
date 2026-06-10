from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    SubmissionStatus,
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TrainerReviewRequest,
)


class TestSubmissionStatus:
    def test_all_expected_statuses_present(self):
        values = {s.value for s in SubmissionStatus}
        assert values == {"ASSIGNED", "IN_PROGRESS", "COMPLETED", "EVALUATED", "GRADED", "ABANDONED"}


class TestTestSubmissionCreate:
    def test_valid_minimal(self):
        sub = TestSubmissionCreate(test_id=1, user_id=2)
        assert sub.test_id == 1
        assert sub.user_id == 2
        assert sub.status == SubmissionStatus.ASSIGNED

    def test_timezone_stripped_from_due_date(self):
        aware_dt = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
        sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=aware_dt)
        assert sub.due_date is not None
        assert sub.due_date.tzinfo is None

    def test_naive_due_date_unchanged(self):
        naive_dt = datetime(2025, 6, 1, 12, 0)
        sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=naive_dt)
        assert sub.due_date == naive_dt

    def test_none_due_date(self):
        sub = TestSubmissionCreate(test_id=1, user_id=2, due_date=None)
        assert sub.due_date is None

    @pytest.mark.parametrize("status", list(SubmissionStatus))
    def test_all_statuses_accepted(self, status):
        sub = TestSubmissionCreate(test_id=1, user_id=2, status=status)
        assert sub.status == status

    def test_missing_test_id_raises(self):
        with pytest.raises(ValidationError):
            TestSubmissionCreate(user_id=2)

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            TestSubmissionCreate(test_id=1)


class TestTestSubmissionUpdate:
    def test_all_optional(self):
        update = TestSubmissionUpdate()
        assert update.status is None
        assert update.ai_score is None
        assert update.trainer_score is None
        assert update.feedback is None

    def test_timezone_stripped_from_started_at(self):
        aware_dt = datetime(2025, 6, 1, 8, 0, tzinfo=timezone.utc)
        update = TestSubmissionUpdate(started_at=aware_dt)
        assert update.started_at is not None
        assert update.started_at.tzinfo is None

    def test_timezone_stripped_from_submitted_at(self):
        aware_dt = datetime(2025, 6, 1, 9, 0, tzinfo=timezone.utc)
        update = TestSubmissionUpdate(submitted_at=aware_dt)
        assert update.submitted_at is not None
        assert update.submitted_at.tzinfo is None

    def test_scores_update(self):
        update = TestSubmissionUpdate(ai_score=80, trainer_score=85, final_score=82)
        assert update.ai_score == 80
        assert update.trainer_score == 85
        assert update.final_score == 82


class TestBulkAssignRequest:
    def test_valid(self):
        req = BulkAssignRequest(test_id=1, participant_emails=["a@example.com", "b@example.com"])
        assert req.test_id == 1
        assert len(req.participant_emails) == 2

    def test_timezone_stripped_from_due_date(self):
        aware_dt = datetime(2025, 12, 31, tzinfo=timezone.utc)
        req = BulkAssignRequest(test_id=1, participant_emails=["a@example.com"], due_date=aware_dt)
        assert req.due_date is not None
        assert req.due_date.tzinfo is None

    def test_empty_emails_list_accepted(self):
        req = BulkAssignRequest(test_id=1, participant_emails=[])
        assert req.participant_emails == []

    def test_missing_test_id_raises(self):
        with pytest.raises(ValidationError):
            BulkAssignRequest(participant_emails=["a@example.com"])


class TestTrainerReviewRequest:
    def test_valid_score_only(self):
        req = TrainerReviewRequest(trainer_score=85)
        assert req.trainer_score == 85
        assert req.feedback is None
        assert req.trainer_evaluation is None

    def test_with_feedback(self):
        req = TrainerReviewRequest(trainer_score=90, feedback="Good work!")
        assert req.feedback == "Good work!"

    def test_with_evaluation_dict(self):
        evaluation = {"strengths": ["clear thinking"], "improvements": ["explain more"]}
        req = TrainerReviewRequest(trainer_score=75, trainer_evaluation=evaluation)
        assert req.trainer_evaluation == evaluation

    def test_trainer_score_required(self):
        with pytest.raises(ValidationError):
            TrainerReviewRequest()
