"""Phase 1 tests: quiz submit finalizes the linked TestSubmission, scores stay
fractional, trainer-score validation holds, and trainer queues enforce ownership.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest
from conftest import make_test
from pydantic import ValidationError
from src.models.test_submission import SubmissionStatus, TestSubmission
from src.schemas.test_submission_schema import TrainerReviewRequest
from src.services.quiz_session_service import QuizSessionService
from src.services.test_submission_service import TestSubmissionService


async def _make_submission(session, *, test_id, user_id, status=SubmissionStatus.ASSIGNED):
    sub = TestSubmission(test_id=test_id, user_id=user_id, status=status)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


def _session_ns(*, submission_id, user_id, test_id):
    return SimpleNamespace(
        submission_id=submission_id,
        user_id=user_id,
        test_id=test_id,
        server_started_at=datetime(2026, 1, 1, 9, 0, 0),
    )


@pytest.mark.asyncio
async def test_finalize_updates_linked_submission(async_session):
    test = await make_test(async_session)
    sub = await _make_submission(async_session, test_id=test.id, user_id=42)
    now = datetime(2026, 1, 1, 10, 0, 0)

    await QuizSessionService._finalize_linked_submission(
        async_session, _session_ns(submission_id=sub.id, user_id=42, test_id=test.id), 66.6667, now
    )
    await async_session.commit()
    await async_session.refresh(sub)

    assert sub.status == SubmissionStatus.COMPLETED
    assert sub.submitted_at == now
    assert sub.started_at == datetime(2026, 1, 1, 9, 0, 0)
    # Fractional score must not be truncated.
    assert abs(sub.final_score - 66.6667) < 1e-6
    assert abs(sub.ai_score - 66.6667) < 1e-6


@pytest.mark.asyncio
async def test_finalize_preserves_existing_started_at(async_session):
    test = await make_test(async_session)
    sub = await _make_submission(async_session, test_id=test.id, user_id=1)
    sub.started_at = datetime(2025, 12, 31, 8, 0, 0)
    await async_session.commit()

    await QuizSessionService._finalize_linked_submission(
        async_session, _session_ns(submission_id=sub.id, user_id=1, test_id=test.id), 100.0,
        datetime(2026, 1, 1, 10, 0, 0),
    )
    await async_session.commit()
    await async_session.refresh(sub)
    # started_at is only filled when missing; not overwritten.
    assert sub.started_at == datetime(2025, 12, 31, 8, 0, 0)


@pytest.mark.asyncio
async def test_finalize_rejects_mismatched_user(async_session):
    test = await make_test(async_session)
    sub = await _make_submission(async_session, test_id=test.id, user_id=42)

    await QuizSessionService._finalize_linked_submission(
        async_session, _session_ns(submission_id=sub.id, user_id=999, test_id=test.id), 80.0,
        datetime(2026, 1, 1, 10, 0, 0),
    )
    await async_session.commit()
    await async_session.refresh(sub)
    # Mismatched session must not mutate the submission.
    assert sub.status == SubmissionStatus.ASSIGNED
    assert sub.final_score is None


@pytest.mark.asyncio
async def test_finalize_noop_without_linked_submission(async_session):
    # submission_id None → returns cleanly, no error.
    await QuizSessionService._finalize_linked_submission(
        async_session, _session_ns(submission_id=None, user_id=1, test_id=1), 50.0,
        datetime(2026, 1, 1, 10, 0, 0),
    )


def test_trainer_review_score_bounds():
    assert TrainerReviewRequest(trainer_score=80.5).trainer_score == 80.5
    for bad in (-1, 150):
        with pytest.raises(ValidationError):
            TrainerReviewRequest(trainer_score=bad)


@pytest.mark.asyncio
async def test_evaluated_queue_enforces_trainer_ownership(async_session, monkeypatch):
    # Avoid real user-service calls during name enrichment.
    class _FakeResp:
        status_code = 404

        def json(self):
            return {}

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return _FakeResp()

    import src.services.test_submission_service as svc
    monkeypatch.setattr(svc.httpx, "AsyncClient", lambda *a, **k: _FakeClient())

    t1 = await make_test(async_session)
    t2 = await make_test(async_session)
    t1.created_by_id = 100
    t2.created_by_id = 200
    await async_session.commit()

    await _make_submission(async_session, test_id=t1.id, user_id=1, status=SubmissionStatus.EVALUATED)
    await _make_submission(async_session, test_id=t2.id, user_id=2, status=SubmissionStatus.EVALUATED)

    owned = await TestSubmissionService.get_evaluated_submissions_for_trainer(async_session, 100)
    assert {s.test_id for s in owned} == {t1.id}
