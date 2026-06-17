import secrets
import uuid
from datetime import datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.session import Session, SessionStatus
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.session_answer_repository import SessionAnswerRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.schemas.session_schema import AnswerResponse, AnswerSubmit, SessionCreate, SessionOut
from src.scoring import exact_match, partial_credit


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
            question_ids=question_ids,
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

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: uuid.UUID,
        answer_in: AnswerSubmit,
        user_id: int,
        http_client: httpx.AsyncClient,
        idempotency_key: str | None,
        correlation_id: str | None,
    ) -> AnswerResponse:
        headers: dict[str, str] = {}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        # 1. Idempotency check — return cached response without re-scoring
        if idempotency_key:
            cached = await IdempotencyRepository.get_by_key(db, idempotency_key)
            if cached:
                return AnswerResponse(**cached.response_json)

        # 2. Acquire row-level lock on the session
        session = await SessionRepository.get_by_id_for_update(db, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        # 3. Guard: reject mutations on closed sessions
        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session is already completed or expired",
            )

        # 4. Validate the submitted question matches the expected position
        question_ids: list[str] = session.question_ids or []
        if not question_ids or session.current_index >= len(question_ids):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No question at current index")
        expected_qid = question_ids[session.current_index]
        if answer_in.question_id != expected_qid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Expected question {expected_qid}, got {answer_in.question_id}",
            )

        # 5. Fetch question body to obtain correct_answers and question_type
        try:
            q_resp = await http_client.get(
                f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/{answer_in.question_id}",
                headers=headers,
            )
            q_resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"question-service error: {e}") from e
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Cannot reach question-service: {e}") from e

        question_body: dict = q_resp.json()
        question_type: str = question_body.get("question_type", "SINGLE_SELECT")
        correct_answers: list[str] = question_body.get("correct_answers", [])

        # 6. Score
        if question_type == "MULTI_SELECT":
            result = partial_credit.score_question(question_type, correct_answers, answer_in.submitted_answers)
        else:
            result = exact_match.score_question(question_type, correct_answers, answer_in.submitted_answers)

        # 7. Persist answer record
        await SessionAnswerRepository.create(
            db,
            session_id=session.session_id,
            question_id=answer_in.question_id,
            question_index=session.current_index,
            submitted_answers=answer_in.submitted_answers,
            earned_points=result.earned,
            max_points=result.max_points,
            is_correct=result.is_correct,
        )

        # 8. Advance position; finalise if all questions answered
        session.current_index += 1
        next_question: dict | None = None

        if session.current_index >= len(question_ids):
            session.status = SessionStatus.COMPLETED
            session.submitted_at = datetime.utcnow()
        else:
            next_qid = question_ids[session.current_index]
            try:
                nq_resp = await http_client.get(
                    f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/{next_qid}",
                    headers=headers,
                )
                nq_resp.raise_for_status()
                next_question = nq_resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError):
                # Non-fatal: answer is already scored; client can retry for the next question body
                next_question = {"id": next_qid}

        # 9. Build response
        response = AnswerResponse(
            question_id=answer_in.question_id,
            earned_points=result.earned,
            max_points=result.max_points,
            is_correct=result.is_correct,
            next_question=next_question,
            session_status=session.status.value,
            current_index=session.current_index,
        )

        # 10. Persist idempotency record and commit everything in one transaction
        if idempotency_key:
            await IdempotencyRepository.create(
                db,
                key=idempotency_key,
                session_id=session.session_id,
                response_json=response.model_dump(),
            )

        await db.commit()
        return response
