"""Quiz session service tests against the in-memory async session.

Only cross-service HTTP to question-management-service is mocked, via the
singleton client patched at the service-module boundary.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.quiz_session import QuizSession, QuizSessionStatus
from src.models.skill import Skill
from src.models.test import Test, TestType
from src.models.test_skill import TestSkill
from src.repositories.quiz_session_repository import QuizSessionRepository
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

    async def test_question_service_unreachable_raises_503(self, db_session):
        test = await make_quiz(db_session, number_of_questions=1)
        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        with patch(QUESTION_CLIENT, return_value=client):
            with pytest.raises(QuizSessionError) as exc:
                await QuizSessionService.create_session(db_session, test.id, 42)
        assert exc.value.status_code == 503

    async def test_question_service_non_200_raises_502(self, db_session):
        test = await make_quiz(db_session, number_of_questions=1)
        client = MagicMock()
        client.get = AsyncMock(return_value=make_response(500, None))
        with patch(QUESTION_CLIENT, return_value=client):
            with pytest.raises(QuizSessionError) as exc:
                await QuizSessionService.create_session(db_session, test.id, 42)
        assert exc.value.status_code == 502

    async def test_concurrent_create_race_returns_existing_session(self, db_session):
        test = await make_quiz(db_session, number_of_questions=2)
        docs = [question_doc(1), question_doc(2)]

        now = datetime.utcnow()
        race_winner = QuizSession(
            session_id="race-winner",
            test_id=test.id,
            user_id=42,
            session_token="winner-token",
            question_ids=["q1", "q2"],
            current_index=0,
            status=QuizSessionStatus.ACTIVE,
            created_at=now,
            started_at=now,
            expires_at=now + timedelta(minutes=10),
        )

        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            with patch.object(
                QuizSessionRepository,
                "get_active_by_test_and_user",
                new_callable=AsyncMock,
                side_effect=[None, race_winner],
            ):
                with patch.object(
                    QuizSessionRepository,
                    "create",
                    new_callable=AsyncMock,
                    side_effect=IntegrityError(None, None, Exception("uq")),
                ):
                    result = await QuizSessionService.create_session(
                        db_session, test.id, 42
                    )

        assert result.session_id == "race-winner"
        assert result.session_token == "winner-token"
        assert result.total_questions == 2

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

    async def test_exhausted_index_raises_422(self, db_session):
        # current_index == len(question_ids) — OOB guard must trigger, not IndexError
        session = await self._seed_session(db_session)
        session.current_index = 2  # question_ids has 2 entries (q1, q2)
        await db_session.commit()
        with pytest.raises(QuizSessionError) as exc:
            await QuizSessionService.get_session(db_session, "sess-1", 42)
        assert exc.value.status_code == 422


@pytest.mark.asyncio
class TestCreateSessionExpiredResume:
    async def test_expired_active_session_is_transitioned_and_replaced(
        self, db_session
    ):
        # Seed an ACTIVE session that is already past its expiry.
        test = await make_quiz(db_session, number_of_questions=1)
        docs = [question_doc(1)]
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            first = await QuizSessionService.create_session(db_session, test.id, 42)

        # Backdate expires_at so the session appears expired.
        from sqlalchemy import update

        from src.models.quiz_session import QuizSession

        await db_session.execute(
            update(QuizSession)
            .where(QuizSession.session_id == first.session_id)
            .values(
                expires_at=__import__("datetime").datetime.utcnow()
                - __import__("datetime").timedelta(seconds=1)
            )
        )
        await db_session.commit()

        # Re-POST — must create a NEW session and mark the old one EXPIRED.
        with patch(
            QUESTION_CLIENT, return_value=mock_question_client(sample_handler(docs))
        ):
            second = await QuizSessionService.create_session(db_session, test.id, 42)

        assert second.session_id != first.session_id
        # Old session must be EXPIRED, not left as ACTIVE.
        old = await db_session.get(QuizSession, first.session_id)
        assert old.status == QuizSessionStatus.EXPIRED
