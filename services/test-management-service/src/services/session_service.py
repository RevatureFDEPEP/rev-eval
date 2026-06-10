import logging
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from src.models.session import Session, SessionStatus
from src.repositories.session_repository import SessionRepository
from src.schemas.session_schema import SanitizedQuestion, SessionOut
from src.utils import question_client

logger = logging.getLogger(__name__)

# Fallback session length when a test has no configured duration.
_DEFAULT_DURATION = timedelta(seconds=3600)
_DEFAULT_QUESTION_COUNT = 20


class EmptyQuestionBankError(Exception):
    """Raised when the question bank returns no questions to sample."""


def _question_id(q: dict) -> str:
    """QuestionResponse serializes its id under the `_id` alias by default;
    accept either key."""
    return str(q.get("id") or q.get("_id"))


def _sanitize(q: dict) -> SanitizedQuestion:
    """Strip answer fields (correct_answers, sample_answer) before exposing a
    question to the candidate."""
    return SanitizedQuestion(
        id=_question_id(q),
        type=q["type"],
        question_text=q["question_text"],
        options=q.get("options"),
        difficulty=q.get("difficulty"),
        image_url=q.get("image_url"),
    )


class SessionService:

    @staticmethod
    async def create_session(db: AsyncSession, test_id: int, user_id: int) -> SessionOut:
        """Mint a quiz session: server-authoritative timing, a fixed sampled
        question set, and the first (sanitized) question. Persists the row
        before responding.
        """
        test = await SessionRepository.get_test(db, test_id)
        if test is None:
            raise ValueError("Test not found")

        # Server-authoritative timing (tz-naive UTC, matching repo convention).
        server_now = datetime.utcnow()
        duration = test.duration or _DEFAULT_DURATION
        expires_at = server_now + duration

        size = test.number_of_questions or _DEFAULT_QUESTION_COUNT
        questions = await question_client.sample_questions(size)
        if not questions:
            raise EmptyQuestionBankError(
                "No questions available to start a session"
            )

        question_ids = [_question_id(q) for q in questions]
        first_question = _sanitize(questions[0])

        session = Session(
            session_id=uuid4(),
            test_id=test_id,
            user_id=user_id,
            session_token=secrets.token_hex(32),
            server_now=server_now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            current_index=0,
            question_ids=question_ids,
        )
        await SessionRepository.create(db, session)
        logger.info(
            "session created: session_id=%s test_id=%s user_id=%s questions=%d",
            session.session_id, test_id, user_id, len(question_ids),
        )

        return SessionOut(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=session.server_now,
            expires_at=session.expires_at,
            current_index=session.current_index,
            total_questions=len(question_ids),
            question=first_question,
        )
