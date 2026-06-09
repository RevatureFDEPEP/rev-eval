"""Quiz session service tests against the in-memory async session.

Only cross-service HTTP to question-management-service is mocked, via the
singleton client patched at the service-module boundary.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.models.skill import Skill
from src.models.test import Test, TestType
from src.models.test_skill import TestSkill
from src.services.quiz_session_service import QuizSessionError, QuizSessionService

QUESTION_CLIENT = "src.services.quiz_session_service.get_question_client"


def make_response(status_code: int, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def mock_question_client(handler):
    """Return a singleton-client stand-in whose .get dispatches via `handler`."""
    client = MagicMock()
    client.get = AsyncMock(side_effect=handler)
    return client


def question_doc(i: int) -> dict:
    """A question-management-service payload (includes answers, to be stripped)."""
    return {
        "_id": f"q{i}",
        "type": "mcq",
        "question_text": f"Question number {i} with enough text",
        "options": [{"option_id": 1, "text": "A"}, {"option_id": 2, "text": "B"}],
        "correct_answers": [1],
        "answer_explanation": "because A",
        "difficulty": "easy",
        "skills": ["Python"],
        "tags": [],
    }


def sample_handler(docs: list[dict]):
    """Build a .get handler: /sample -> docs; /questions/{id} -> matching doc."""

    by_id = {d["_id"]: d for d in docs}

    async def _handler(url, params=None, headers=None):
        if url.endswith("/sample"):
            return make_response(200, docs)
        qid = url.rsplit("/", 1)[-1]
        return make_response(200, by_id.get(qid))

    return _handler


async def make_quiz(
    db,
    *,
    number_of_questions: int = 3,
    duration_seconds: int | None = 600,
    test_type: TestType = TestType.QUIZ,
    with_skill: bool = True,
) -> Test:
    test = Test(
        name="Sample Quiz",
        test_type=test_type,
        number_of_questions=number_of_questions,
        duration=timedelta(seconds=duration_seconds) if duration_seconds else None,
        active=True,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    if with_skill:
        skill = Skill(name="Python")
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        db.add(TestSkill(test_id=test.id, skill_id=skill.id))
        await db.commit()
    return test


@pytest.mark.asyncio
class TestCreateSession:
    async def test_freezes_questions_and_strips_answers(self, db_session):
        test = await make_quiz(db_session, number_of_questions=3)
        docs = [question_doc(1), question_doc(2), question_doc(3)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            resp = await QuizSessionService.create_session(db_session, test.id, 42)

        assert resp.total_questions == 3
        assert resp.current_index == 0
        assert resp.status == QuizSessionStatus.ACTIVE
        assert resp.question.id == "q1"
        # answers must not leak through the participant schema
        assert "correct_answers" not in resp.question.model_dump()
        assert "answer_explanation" not in resp.question.model_dump()
        # timing is server-derived
        assert resp.expires_at == resp.server_now + timedelta(seconds=600)
        # the ordered selection is frozen on the session row
        persisted = await db_session.get(QuizSession, resp.session_id)
        assert persisted.question_ids == ["q1", "q2", "q3"]

    async def test_default_duration_when_test_has_none(self, db_session):
        test = await make_quiz(db_session, number_of_questions=1, duration_seconds=None)
        docs = [question_doc(1)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            resp = await QuizSessionService.create_session(db_session, test.id, 7)
        # falls back to DEFAULT_QUIZ_DURATION_MINUTES (30) * 60
        assert resp.expires_at == resp.server_now + timedelta(minutes=30)

    async def test_insufficient_questions_raises_409(self, db_session):
        test = await make_quiz(db_session, number_of_questions=5)
        docs = [question_doc(1), question_doc(2)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            with pytest.raises(QuizSessionError) as exc:
                await QuizSessionService.create_session(db_session, test.id, 42)
        assert exc.value.status_code == 409

    async def test_idempotent_returns_existing_active_session(self, db_session):
        test = await make_quiz(db_session, number_of_questions=2)
        docs = [question_doc(1), question_doc(2)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            first = await QuizSessionService.create_session(db_session, test.id, 42)
            second = await QuizSessionService.create_session(db_session, test.id, 42)
        assert first.session_id == second.session_id
        assert first.session_token == second.session_token

    async def test_rejects_non_quiz_test(self, db_session):
        test = await make_quiz(db_session, test_type=TestType.INTERVIEW)
        with pytest.raises(QuizSessionError) as exc:
            await QuizSessionService.create_session(db_session, test.id, 42)
        assert exc.value.status_code == 400

    async def test_missing_test_raises_value_error(self, db_session):
        with pytest.raises(ValueError):
            await QuizSessionService.create_session(db_session, 9999, 42)

    async def test_no_skills_raises_422(self, db_session):
        test = await make_quiz(db_session, with_skill=False)
        with pytest.raises(QuizSessionError) as exc:
            await QuizSessionService.create_session(db_session, test.id, 42)
        assert exc.value.status_code == 422

    async def test_tokens_are_unique(self, db_session):
        t1 = await make_quiz(db_session, number_of_questions=1)
        t2 = await make_quiz(db_session, number_of_questions=1)
        docs = [question_doc(1)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            a = await QuizSessionService.create_session(db_session, t1.id, 1)
            b = await QuizSessionService.create_session(db_session, t2.id, 1)
        assert a.session_token != b.session_token
        assert len(a.session_token) > 20


@pytest.mark.asyncio
class TestGetSession:
    async def _seed_session(
        self, db, *, user_id=42, expires_delta=timedelta(minutes=5)
    ):
        now = datetime.utcnow()
        session = QuizSession(
            session_id="sess-1",
            test_id=1,
            user_id=user_id,
            session_token="tok-1",
            question_ids=["q1", "q2"],
            current_index=0,
            status=QuizSessionStatus.ACTIVE,
            created_at=now,
            started_at=now,
            expires_at=now + expires_delta,
        )
        db.add(session)
        await db.commit()
        return session

    async def test_lazy_expires_past_session(self, db_session):
        await self._seed_session(db_session, expires_delta=timedelta(minutes=-1))
        docs = [question_doc(1), question_doc(2)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            resp = await QuizSessionService.get_session(db_session, "sess-1", 42)
        assert resp.status == QuizSessionStatus.EXPIRED

    async def test_active_session_returns_current_question(self, db_session):
        await self._seed_session(db_session)
        docs = [question_doc(1), question_doc(2)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            resp = await QuizSessionService.get_session(db_session, "sess-1", 42)
        assert resp.status == QuizSessionStatus.ACTIVE
        assert resp.question.id == "q1"
        assert "correct_answers" not in resp.question.model_dump()

    async def test_wrong_user_rejected_403(self, db_session):
        await self._seed_session(db_session, user_id=42)
        with pytest.raises(QuizSessionError) as exc:
            await QuizSessionService.get_session(db_session, "sess-1", 99)
        assert exc.value.status_code == 403

    async def test_missing_session_raises_value_error(self, db_session):
        with pytest.raises(ValueError):
            await QuizSessionService.get_session(db_session, "nope", 42)
