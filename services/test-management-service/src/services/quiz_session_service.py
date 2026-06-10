"""
Quiz session creation and retrieval.

Mints a server-timed quiz session: selects a frozen, ordered set of questions
from question-management-service (via MongoDB $sample), records
server-authoritative timing, and returns the first question with answers
stripped. The client never computes timing state.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.quiz_session import QuizSessionStatus
from src.models.test import TestType
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.schemas.quiz_session_schema import (
    ParticipantQuestion,
    SessionCreateResponse,
    SessionStateResponse,
)
from src.utils.logging_config import get_correlation_id
from src.utils.question_client import get_question_client

logger = logging.getLogger(__name__)


class QuizSessionError(Exception):
    """Domain error carrying an HTTP status code for the route to surface."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _participant_question(raw: dict, index: int) -> ParticipantQuestion:
    """Map a question-management-service payload to the answer-free schema."""
    return ParticipantQuestion(
        id=raw["_id"],
        type=raw["type"],
        question_text=raw["question_text"],
        options=raw.get("options"),
        difficulty=raw.get("difficulty"),
        index=index,
    )


class QuizSessionService:
    @staticmethod
    async def _get_skill_names(db: AsyncSession, test_id: int) -> list[str]:
        links = await TestSkillRepository.list_by_test(db, test_id)
        if not links:
            return []
        skills = await SkillRepository.get_by_ids(db, [link.skill_id for link in links])
        return [s.name for s in skills if s.name]

    @staticmethod
    async def _sample_questions(skills: list[str], count: int) -> list[dict]:
        """Call question-management-service /questions/sample and return raw dicts."""
        url = f"{settings.QUESTION_MANAGEMENT_SERVICE_URL}/v1/api/questions/sample"
        params = [("skills", s) for s in skills]
        params.append(("count", str(count)))
        client = get_question_client()
        try:
            response = await client.get(
                url,
                params=params,
                headers={"X-Correlation-Id": get_correlation_id()},
            )
        except httpx.RequestError as e:
            logger.error("Failed to reach question-management-service: %s", e)
            raise QuizSessionError(
                "Cannot reach question-management-service", status_code=503
            ) from e
        if response.status_code != 200:
            logger.error(
                "question-management-service /sample returned %s", response.status_code
            )
            raise QuizSessionError(
                "question-management-service error while sampling questions",
                status_code=502,
            )
        return response.json()

    @staticmethod
    async def _fetch_question(question_id: str) -> dict:
        """Fetch a single question body from question-management-service."""
        url = (
            f"{settings.QUESTION_MANAGEMENT_SERVICE_URL}/v1/api/questions/{question_id}"
        )
        client = get_question_client()
        try:
            response = await client.get(
                url, headers={"X-Correlation-Id": get_correlation_id()}
            )
        except httpx.RequestError as e:
            logger.error("Failed to reach question-management-service: %s", e)
            raise QuizSessionError(
                "Cannot reach question-management-service", status_code=503
            ) from e
        if response.status_code != 200:
            raise QuizSessionError(
                "Could not load the current question", status_code=502
            )
        return response.json()

    @staticmethod
    async def create_session(
        db: AsyncSession, test_id: int, user_id: int
    ) -> SessionCreateResponse:
        test = await TestRepository.get_by_id(db, test_id)
        if not test:
            raise ValueError("Test not found")
        if test.test_type != TestType.QUIZ:
            raise QuizSessionError("Test is not a quiz", status_code=400)

        now = datetime.now(UTC).replace(tzinfo=None)

        # Idempotent: reuse an existing, non-expired active session.
        existing = await QuizSessionRepository.get_active_by_test_and_user(
            db, test_id, user_id
        )
        if existing:
            if existing.expires_at <= now:
                # Transition the stale row to EXPIRED before creating a new one,
                # so we never have two ACTIVE rows for the same (test_id, user_id).
                await QuizSessionRepository.set_status(
                    db, existing, QuizSessionStatus.EXPIRED
                )
            else:
                raw = await QuizSessionService._fetch_question(
                    existing.question_ids[existing.current_index]
                )
                question = _participant_question(raw, existing.current_index)
                return SessionCreateResponse(
                    session_id=existing.session_id,
                    session_token=existing.session_token,
                    status=existing.status,
                    server_now=now,
                    expires_at=existing.expires_at,
                    total_questions=len(existing.question_ids),
                    current_index=existing.current_index,
                    question=question,
                )

        skill_names = await QuizSessionService._get_skill_names(db, test_id)
        if not skill_names:
            raise QuizSessionError(
                "Test has no skills configured; cannot select questions",
                status_code=422,
            )

        count = test.number_of_questions or 20
        sample = await QuizSessionService._sample_questions(skill_names, count)
        if len(sample) < count:
            raise QuizSessionError(
                f"Not enough questions for the test's skills: "
                f"needed {count}, found {len(sample)}",
                status_code=409,
            )

        question_ids = [q["_id"] for q in sample]

        duration_seconds = test.duration_seconds or (
            settings.DEFAULT_QUIZ_DURATION_MINUTES * 60
        )
        expires_at = now + timedelta(seconds=duration_seconds)

        try:
            session = await QuizSessionRepository.create(
                db,
                session_id=str(uuid.uuid4()),
                test_id=test_id,
                user_id=user_id,
                session_token=secrets.token_urlsafe(32),
                question_ids=question_ids,
                started_at=now,
                expires_at=expires_at,
            )
        except IntegrityError:
            # A concurrent POST raced past the idempotency check and won the
            # insert first. Roll back and return the session that row already owns.
            await db.rollback()
            race_winner = await QuizSessionRepository.get_active_by_test_and_user(
                db, test_id, user_id
            )
            if not race_winner:
                raise QuizSessionError(
                    "Session conflict; please retry", status_code=409
                )
            raw = await QuizSessionService._fetch_question(
                race_winner.question_ids[race_winner.current_index]
            )
            question = _participant_question(raw, race_winner.current_index)
            return SessionCreateResponse(
                session_id=race_winner.session_id,
                session_token=race_winner.session_token,
                status=race_winner.status,
                server_now=now,
                expires_at=race_winner.expires_at,
                total_questions=len(race_winner.question_ids),
                current_index=race_winner.current_index,
                question=question,
            )

        question = _participant_question(sample[0], 0)
        return SessionCreateResponse(
            session_id=session.session_id,
            session_token=session.session_token,
            status=session.status,
            server_now=now,
            expires_at=session.expires_at,
            total_questions=len(question_ids),
            current_index=0,
            question=question,
        )

    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: str, user_id: int
    ) -> SessionStateResponse:
        session = await QuizSessionRepository.get_by_id(db, session_id)
        if not session:
            raise ValueError("Session not found")
        if session.user_id != user_id:
            raise QuizSessionError("Not authorized for this session", status_code=403)

        now = datetime.now(UTC).replace(tzinfo=None)

        if session.status == QuizSessionStatus.ACTIVE and session.expires_at <= now:
            session = await QuizSessionRepository.set_status(
                db, session, QuizSessionStatus.EXPIRED
            )

        if session.current_index >= len(session.question_ids):
            raise QuizSessionError(
                "Session has no remaining questions", status_code=422
            )

        raw = await QuizSessionService._fetch_question(
            session.question_ids[session.current_index]
        )
        question = _participant_question(raw, session.current_index)
        return SessionStateResponse(
            session_id=session.session_id,
            status=session.status,
            server_now=now,
            expires_at=session.expires_at,
            total_questions=len(session.question_ids),
            current_index=session.current_index,
            question=question,
        )
