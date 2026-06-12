# src/services/session_service.py
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.answer import QuizAnswer
from src.models.session import QuizSession, SessionStatus
from src.repositories.answer_repository import AnswerRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.answer_schema import AnswerCreate, AnswerResponse
from src.schemas.session_schema import SessionResponse
from src.scoring import partial_credit
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
        # Direct service-to-service call (bypasses the gateway), so we present
        # the trainer role ourselves to satisfy question-mgmt's guard on the
        # answer-bearing read surface. Safe: the gateway overwrites X-User-Role
        # from the verified JWT, so browser traffic can never forge this.
        headers = {"X-User-Role": "TRAINER"}
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

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: str,
        user_id: int,
        body: AnswerCreate,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> AnswerResponse:
        """Score the answer to the session's current question, then advance.

        Wraps the read-modify-write in one transaction and locks the session row
        (``SELECT FOR UPDATE``) so concurrent retries queue rather than race on
        ``current_index``. A repeated ``Idempotency-Key`` replays the stored
        response without re-scoring or re-advancing. Answering the final
        question transitions the session to SUBMITTED and rejects all further
        mutations with 409.
        """
        # Fast-path replay (re-checked under the row lock below to close the
        # concurrent-duplicate window).
        if idempotency_key:
            prior = await AnswerRepository.get_by_idempotency_key(db, idempotency_key)
            if prior is not None:
                return AnswerResponse(**prior.response_payload)

        session = await SessionRepository.get_by_id_for_update(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        if session.user_id != user_id:
            # Don't leak existence to other users.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This session belongs to another user",
            )

        # Re-check idempotency now that the row is locked: a concurrent request
        # with the same key was serialized behind us and has already committed.
        if idempotency_key:
            prior = await AnswerRepository.get_by_idempotency_key(db, idempotency_key)
            if prior is not None:
                await db.rollback()
                return AnswerResponse(**prior.response_payload)

        now = datetime.utcnow()

        # Lazily finalize an expired-but-still-ACTIVE session.
        if session.status == SessionStatus.ACTIVE and session.expires_at < now:
            session.status = SessionStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has expired",
            )

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session is {session.status.value}; no further answers accepted",
            )

        question_ids = session.question_ids or []
        idx = session.current_index
        if idx >= len(question_ids):
            # Index already past the snapshot — treat as finalized.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No current question to answer",
            )

        current_qid = question_ids[idx]
        if body.question_id is not None and body.question_id != current_qid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Out-of-order answer: current question is index {idx} "
                    f"({current_qid}), not {body.question_id}"
                ),
            )

        question = await SessionService._fetch_question(current_qid, correlation_id)
        result = partial_credit.score_question(
            question.get("type"),
            question.get("correct_answers"),
            body.submitted_answers,
        )

        # Advance; finalize if that was the last question.
        new_index = idx + 1
        finished = new_index >= len(question_ids)
        session.current_index = new_index
        if finished:
            session.status = SessionStatus.SUBMITTED
            session.submitted_at = now

        response = AnswerResponse(
            is_correct=result.is_correct,
            score=result.score,
            algorithm=result.algorithm,
            current_index=new_index,
            status=session.status,
            finished=finished,
        )

        AnswerRepository.add(
            db,
            QuizAnswer(
                session_id=session.session_id,
                question_id=current_qid,
                question_index=idx,
                submitted_answers=body.submitted_answers,
                is_correct=result.is_correct,
                score=result.score,
                algorithm=result.algorithm,
                idempotency_key=idempotency_key,
                response_payload=response.model_dump(mode="json"),
            ),
        )

        try:
            await db.commit()
        except IntegrityError:
            # Lost an idempotency-key race against a different session's commit;
            # replay the now-stored response.
            await db.rollback()
            if idempotency_key:
                prior = await AnswerRepository.get_by_idempotency_key(db, idempotency_key)
                if prior is not None:
                    return AnswerResponse(**prior.response_payload)
            raise
        return response

    @staticmethod
    async def _fetch_question(question_id: str, correlation_id: str | None) -> dict:
        """Fetch one question (including ``correct_answers``) from
        question-management-service via the httpx singleton, for server-side
        scoring. The answer key never reaches the client through this path."""
        url = f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/{question_id}"
        # Trainer role for the gateway-guarded answer-bearing endpoint (see
        # _fetch_sample). The answer key never reaches the client via this path.
        headers = {"X-User-Role": "TRAINER"}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        client = get_http_client()
        try:
            response = await client.get(url, headers=headers)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach question-management-service: {e}",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Sampled question {question_id} no longer exists",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"question-management-service returned {response.status_code}",
            )
        return response.json()
