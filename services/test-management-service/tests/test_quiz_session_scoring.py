"""Scoring service tests against the in-memory async session.

QMS HTTP calls are mocked at the service-module boundary exactly as in
test_quiz_session_service.py.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.schemas.session_answer_schema import AnswerSubmitRequest
from src.services.quiz_session_scoring_service import QuizSessionScoringService
from src.services.quiz_session_service import QuizSessionError

SCORING_CLIENT = "src.services.quiz_session_service.get_question_client"


# ---------------------------------------------------------------------------
# Helpers (mirror test_quiz_session_service.py patterns)
# ---------------------------------------------------------------------------


def make_response(status_code: int, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def mock_question_client(handler):
    client = MagicMock()
    client.get = AsyncMock(side_effect=handler)
    return client


def question_doc(i: int, q_type: str = "mcq") -> dict:
    return {
        "_id": f"q{i}",
        "type": q_type,
        "question_text": f"Question number {i} with enough text",
        "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
        "correct_answers": [1],
        "answer_explanation": "because A",
        "difficulty": "easy",
        "skills": ["Python"],
        "tags": [],
    }


def fetch_handler(docs: list[dict]):
    """Handler that serves individual questions by ID only (no /sample)."""
    by_id = {d["_id"]: d for d in docs}

    async def _handler(url, params=None, headers=None):
        qid = url.rsplit("/", 1)[-1]
        doc = by_id.get(qid)
        return make_response(200 if doc else 404, doc)

    return _handler


async def seed_session(
    db,
    question_ids: list[str],
    user_id: int = 1,
    test_id: int = 1,
    status: QuizSessionStatus = QuizSessionStatus.ACTIVE,
    expires_delta: timedelta = timedelta(hours=1),
) -> QuizSession:
    now = datetime.now(UTC).replace(tzinfo=None)
    session = QuizSession(
        session_id=str(uuid.uuid4()),
        test_id=test_id,
        user_id=user_id,
        session_token=secrets.token_urlsafe(32),
        question_ids=question_ids,
        current_index=0,
        status=status,
        started_at=now,
        expires_at=now + expires_delta,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


def make_request(question_id: str, answers=None) -> AnswerSubmitRequest:
    return AnswerSubmitRequest(
        question_id=question_id,
        submitted_answers=answers if answers is not None else [1],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_advances_index(db_session):
    """Correct answer scored, current_index advances, next question returned."""
    docs = [question_doc(0), question_doc(1)]
    session = await seed_session(db_session, ["q0", "q1"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        result = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), "idem-happy-01"
        )

    assert result.is_correct is True
    assert result.points_earned == 1.0
    assert result.current_index == 1
    assert result.question is not None
    assert result.question.id == "q1"
    assert result.session_status == QuizSessionStatus.ACTIVE
    assert result.submitted_at is None


@pytest.mark.asyncio
async def test_final_answer_submits_session(db_session):
    """Answering the last question transitions session to SUBMITTED."""
    docs = [question_doc(0)]
    session = await seed_session(db_session, ["q0"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        result = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), "idem-final-01"
        )

    assert result.session_status == QuizSessionStatus.SUBMITTED
    assert result.question is None
    assert result.submitted_at is not None
    # submitted_at is naive-UTC; it must serialize with an explicit UTC offset
    # so the client doesn't read it as local time (shared UtcDatetime serializer).
    assert result.model_dump(mode="json")["submitted_at"].endswith("+00:00")
    # Finalize advances current_index to total so a completed quiz reports all
    # questions consumed (not total-1).
    assert result.current_index == 1
    assert result.total_questions == 1


@pytest.mark.asyncio
async def test_wrong_answer_scores_zero(db_session):
    docs = [question_doc(0), question_doc(1)]
    session = await seed_session(db_session, ["q0", "q1"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        result = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [2]), "idem-wrong-01"
        )

    assert result.is_correct is False
    assert result.points_earned == 0.0
    assert result.current_index == 1


@pytest.mark.asyncio
async def test_idempotency_key_returns_cached_result(db_session):
    """Second call with the same Idempotency-Key returns cached result without re-scoring."""
    docs = [question_doc(0), question_doc(1)]
    session = await seed_session(db_session, ["q0", "q1"])
    key = "idem-key-001"

    client_mock = mock_question_client(fetch_handler(docs))
    with patch(SCORING_CLIENT, return_value=client_mock):
        r1 = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), key
        )
        fetch_count_after_first = client_mock.get.call_count

        r2 = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), key
        )

    # Second call fetches the next question to build the response, not re-score.
    assert r1.is_correct == r2.is_correct
    assert r1.points_earned == r2.points_earned
    # QMS was NOT called an extra time for scoring on the duplicate
    assert client_mock.get.call_count == fetch_count_after_first + 1


@pytest.mark.asyncio
async def test_expired_session_raises_409(db_session):
    session = await seed_session(
        db_session, ["q0"], expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(QuizSessionError) as exc_info:
        await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0"), None
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_expired_session_is_finalized_at_timeout(db_session):
    """Option A: hitting an expired attempt finalizes it — status EXPIRED with
    submitted_at set to the timeout moment, so partial answers count as a
    terminal result for reporting (distinct from a real SUBMITTED)."""
    session = await seed_session(
        db_session, ["q0"], expires_delta=timedelta(seconds=-5)
    )
    expires_at = session.expires_at
    assert session.submitted_at is None

    with pytest.raises(QuizSessionError):
        await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0"), None
        )

    await db_session.refresh(session)
    assert session.status == QuizSessionStatus.EXPIRED
    assert session.submitted_at == expires_at


@pytest.mark.asyncio
async def test_submitted_session_raises_409(db_session):
    session = await seed_session(db_session, ["q0"], status=QuizSessionStatus.SUBMITTED)

    with pytest.raises(QuizSessionError) as exc_info:
        await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0"), None
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_wrong_question_id_raises_422(db_session):
    docs = [question_doc(0), question_doc(1)]
    session = await seed_session(db_session, ["q0", "q1"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        with pytest.raises(QuizSessionError) as exc_info:
            await QuizSessionScoringService.submit_answer(
                db_session,
                session.session_id,
                1,
                make_request("q1"),  # wrong — current is q0
                None,
            )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_unauthorized_user_raises_403(db_session):
    session = await seed_session(db_session, ["q0"], user_id=1)

    with pytest.raises(QuizSessionError) as exc_info:
        await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 99, make_request("q0"), None
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_text_question_advances_with_manual_review(db_session):
    """TEXT questions score 0 + requires_manual_review but the session still advances."""
    text_doc = {
        "_id": "qt0",
        "type": "text",
        "question_text": "Explain recursion in your own words",
        "options": None,
        "correct_answers": None,
        "difficulty": "medium",
        "skills": ["Python"],
        "tags": [],
    }
    docs = [text_doc, question_doc(1)]
    session = await seed_session(db_session, ["qt0", "q1"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        result = await QuizSessionScoringService.submit_answer(
            db_session,
            session.session_id,
            1,
            make_request("qt0", ["Recursion is when a function calls itself"]),
            "idem-text-01",
        )

    assert result.points_earned == 0.0
    assert result.requires_manual_review is True
    assert result.current_index == 1
    assert result.question is not None
    assert result.question.id == "q1"


@pytest.mark.asyncio
async def test_final_answer_retry_is_idempotent(db_session):
    """Retrying the FINAL answer with the same key replays the cached result
    instead of hitting the 'already submitted' 409 guard."""
    docs = [question_doc(0)]
    session = await seed_session(db_session, ["q0"])
    key = "idem-final-001"

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        r1 = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), key
        )
        # Session is now SUBMITTED; the retry must NOT raise 409.
        r2 = await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), key
        )

    assert r1.session_status == QuizSessionStatus.SUBMITTED
    assert r2.session_status == QuizSessionStatus.SUBMITTED
    assert r2.is_correct == r1.is_correct
    assert r2.points_earned == r1.points_earned
    assert r2.question is None


@pytest.mark.asyncio
async def test_advance_index_prevents_resubmitting_same_question(db_session):
    """After a normal submit the index advances, so replaying the same question
    mismatches the current one and is rejected (422) rather than double-scored."""
    docs = [question_doc(0), question_doc(1)]
    session = await seed_session(db_session, ["q0", "q1"])

    with patch(SCORING_CLIENT, return_value=mock_question_client(fetch_handler(docs))):
        await QuizSessionScoringService.submit_answer(
            db_session, session.session_id, 1, make_request("q0", [1]), "idem-adv-01"
        )
        # A fresh key (so it is not an idempotent replay) still mismatches the
        # now-advanced current_index and is rejected.
        with pytest.raises(QuizSessionError) as exc_info:
            await QuizSessionScoringService.submit_answer(
                db_session,
                session.session_id,
                1,
                make_request("q0", [1]),
                "idem-adv-02",
            )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_unique_constraint_blocks_double_score_at_same_index(db_session):
    """Durable backstop: the (session_id, question_index) unique constraint
    rejects a second answer row for the same question, covering the concurrent /
    no-lock (SQLite) case the row lock cannot. The two writes carry *different*
    idempotency keys, so the rejection comes from the question_index constraint
    rather than the idempotency one."""
    from sqlalchemy.exc import IntegrityError

    from src.repositories.session_answer_repository import SessionAnswerRepository

    session = await seed_session(db_session, ["q0", "q1"])
    common = dict(
        session_id=session.session_id,
        question_id="q0",
        question_index=0,
        submitted_answers=[1],
        is_correct=True,
        points_earned=1.0,
    )
    SessionAnswerRepository.add(db_session, **common, idempotency_key="idem-dup-01")
    await db_session.commit()

    SessionAnswerRepository.add(db_session, **common, idempotency_key="idem-dup-02")
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_qms_unreachable_raises_503(db_session):
    """A network failure reaching QMS while scoring surfaces as 503."""
    session = await seed_session(db_session, ["q0", "q1"])

    async def _raise(url, params=None, headers=None):
        raise httpx.RequestError("connection refused")

    with patch(SCORING_CLIENT, return_value=mock_question_client(_raise)):
        with pytest.raises(QuizSessionError) as exc_info:
            await QuizSessionScoringService.submit_answer(
                db_session, session.session_id, 1, make_request("q0", [1]), None
            )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_qms_error_status_raises_502(db_session):
    """A non-200 from QMS while scoring surfaces as 502."""
    session = await seed_session(db_session, ["q0", "q1"])

    async def _error(url, params=None, headers=None):
        return make_response(502, None)

    with patch(SCORING_CLIENT, return_value=mock_question_client(_error)):
        with pytest.raises(QuizSessionError) as exc_info:
            await QuizSessionScoringService.submit_answer(
                db_session, session.session_id, 1, make_request("q0", [1]), None
            )

    assert exc_info.value.status_code == 502
