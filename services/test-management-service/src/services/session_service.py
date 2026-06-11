# src/services/session_service.py
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.session import QuizSession, SessionStatus
from src.repositories.session_repository import SessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.session_schema import SessionResponse
from src.utils.http_client import get_http_client

# Fallback session length when a test has no explicit duration.
_DEFAULT_DURATION = timedelta(minutes=60)


class SessionService:

    @staticmethod
    async def create_session(
        db: AsyncSession,
        test_id: int,
        user_id: int,
        correlation_id: str | None = None,
    ) -> SessionResponse:
        """Start a quiz session for ``test_id`` on behalf of ``user_id``.

        Loads the test, asks question-management-service for a random ``$sample``
        of questions sized to the test, snapshots the sampled IDs, computes the
        server-authoritative clock, and persists the row BEFORE responding so
        the returned token always corresponds to a durable session.
        """
        test = await TestRepository.get_by_id(db, test_id)
        if test is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found",
            )

        limit = test.number_of_questions or 20
        questions = await SessionService._fetch_sample(limit, correlation_id)

        # question-management-service serializes by alias, so the id arrives as
        # "_id" (Mongo ObjectId string); fall back to "id" for resilience.
        question_ids = [
            qid for q in questions if (qid := q.get("_id") or q.get("id"))
        ]
        first_question = questions[0] if questions else None

        server_now = datetime.utcnow()
        duration = test.duration or _DEFAULT_DURATION
        expires_at = server_now + duration

        quiz_session = QuizSession(
            session_id=str(uuid4()),
            test_id=test_id,
            user_id=user_id,
            session_token=secrets.token_hex(32),
            server_now=server_now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            current_index=0,
            question_ids=question_ids,
        )

        # Persist BEFORE responding — the token must map to a durable session.
        saved = await SessionRepository.create(db, quiz_session)

        return SessionResponse(
            session_id=saved.session_id,
            session_token=saved.session_token,
            server_now=saved.server_now,
            expires_at=saved.expires_at,
            first_question=first_question,
        )

    @staticmethod
    async def _fetch_sample(limit: int, correlation_id: str | None) -> list[dict]:
        """Call question-management-service's ``$sample`` endpoint via the
        shared httpx singleton, propagating the correlation id for tracing."""
        url = f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/sample"
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = get_http_client()
        try:
            response = await client.get(url, params={"limit": limit}, headers=headers)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach question-management-service: {e}",
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"question-management-service returned {response.status_code}",
            )
        return response.json()
