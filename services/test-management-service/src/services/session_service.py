import secrets
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.session import Session
from src.repositories.session_repository import SessionRepository
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.schemas.session_schema import SessionCreate, SessionOut


class SessionService:
    @staticmethod
    async def create_session(
        db: AsyncSession,
        session_in: SessionCreate,
        user_id: int,
        http_client: httpx.AsyncClient,
        correlation_id: str | None,
    ) -> SessionOut:
        # 1. Verify test exists
        test = await TestRepository.get_by_id(db, session_in.test_id)
        if not test:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

        # 2. Resolve skill names for this test
        test_skills = await TestSkillRepository.list_by_test(db, session_in.test_id)
        skill_names: list[str] = []
        for link in test_skills:
            skill = await SkillRepository.get_by_id(db, link.skill_id)
            if skill:
                skill_names.append(skill.name)

        # 3. Compute timing (server-authoritative)
        server_now = datetime.utcnow()
        expires_at = server_now + test.duration if test.duration else server_now

        # 4. Sample question IDs from question-management-service
        headers = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        count = test.number_of_questions or 1
        try:
            sample_resp = await http_client.post(
                f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/sample",
                json={"skills": skill_names, "count": count},
                headers=headers,
            )
            sample_resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"question-service error: {e}") from e
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Cannot reach question-service: {e}") from e

        question_ids: list[str] = sample_resp.json().get("question_ids", [])
        if not question_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No questions found for this test's skills")

        # 5. Fetch first question body
        try:
            q_resp = await http_client.get(
                f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/{question_ids[0]}",
                headers=headers,
            )
            q_resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"question-service error: {e}") from e
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Cannot reach question-service: {e}") from e

        first_question: dict = q_resp.json()

        # 6. Persist session (only after both remote calls succeed)
        session = Session(
            test_id=session_in.test_id,
            user_id=user_id,
            session_token=secrets.token_hex(32),
            server_now=server_now,
            expires_at=expires_at,
        )
        session = await SessionRepository.create(db, session)

        # 7. Return response
        return SessionOut(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=session.server_now,
            expires_at=session.expires_at,
            first_question=first_question,
        )
