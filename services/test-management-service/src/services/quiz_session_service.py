import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.models.quiz_session import QuizSession, SessionStatus
from src.models.test import Test, TestType
from src.models.test_skill import TestSkill
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.schemas.quiz_session_schema import CreateSessionRequest, SessionResponse
from src.utils.http_client import call_service

logger = logging.getLogger(__name__)

DEFAULT_DURATION = timedelta(minutes=60)


class QuizSessionService:

    @staticmethod
    async def create_session(
        db: AsyncSession,
        body: CreateSessionRequest,
        user_id: int,
        correlation_id: Optional[str] = None,
    ) -> SessionResponse:
        result = await db.execute(
            select(Test)
            .options(selectinload(Test.test_skills).selectinload(TestSkill.skill))
            .where(Test.id == body.quiz_id)
        )
        test: Optional[Test] = result.scalar_one_or_none()

        if test is None:
            raise ValueError(f"Quiz {body.quiz_id} not found")
        if test.test_type != TestType.QUIZ:
            raise ValueError(f"Test {body.quiz_id} is not a QUIZ")
        if not test.active:
            raise ValueError(f"Quiz {body.quiz_id} is not active")

        server_now = datetime.utcnow()
        duration = test.duration if test.duration else DEFAULT_DURATION
        expires_at = server_now + duration

        session_token = str(uuid.uuid4())

        quiz_session = await QuizSessionRepository.create(
            db,
            session_token=session_token,
            quiz_id=test.id,
            user_id=user_id,
            server_now=server_now,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
        )

        first_question = await QuizSessionService._fetch_first_question(
            test, correlation_id=correlation_id
        )

        return SessionResponse(
            session_token=quiz_session.session_token,
            quiz_id=quiz_session.quiz_id,
            user_id=quiz_session.user_id,
            server_now=quiz_session.server_now,
            expires_at=quiz_session.expires_at,
            first_question=first_question,
        )

    @staticmethod
    async def _fetch_first_question(
        test: Test,
        correlation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        base_url = settings.QUESTION_SERVICE_URL

        skill_name: Optional[str] = None
        if test.test_skills:
            skill_name = test.test_skills[0].skill.name

        try:
            url = (
                f"{base_url}/v1/api/questions/by-skill/{skill_name}"
                if skill_name
                else f"{base_url}/v1/api/questions/"
            )
            response = await call_service(
                "GET", url, correlation_id=correlation_id, timeout=10.0, max_retries=2
            )

            if response.status_code == 200:
                questions = response.json()
                if isinstance(questions, list) and questions:
                    return questions[0]

            # skill filter returned empty — fall back to unfiltered list
            if skill_name:
                fallback = await call_service(
                    "GET",
                    f"{base_url}/v1/api/questions/",
                    correlation_id=correlation_id,
                    timeout=10.0,
                    max_retries=2,
                )
                if fallback.status_code == 200:
                    items = fallback.json()
                    if isinstance(items, list) and items:
                        return items[0]

        except httpx.RequestError as exc:
            logger.warning(
                "Could not reach question-management-service cid=%s: %s",
                correlation_id,
                exc,
            )

        return None
