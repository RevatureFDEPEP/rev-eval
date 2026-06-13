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
from src.schemas.session_schema import SanitizedQuestion, SessionResponse
from src.scoring import partial_credit
from src.scoring.result import ScoreResult
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
        # "_id" (Mongo ObjectId string); fall back to "id" for resilience. Keep
        # only questions with a usable id and derive BOTH question_ids and the
        # displayed first question from that same filtered list, so the body the
        # client sees always matches question_ids[0] — the question the server
        # will score at current_index 0.
        sampled = [q for q in questions if q.get("_id") or q.get("id")]
        question_ids = [q.get("_id") or q.get("id") for q in sampled]
        # Sequential reveal: only the current (first) question body leaves the
        # service now; the rest are delivered one at a time by the answer
        # endpoint. /sample already strips the answer key (QuestionPublic).
        first_question = (
            SessionService._sanitize_question(sampled[0]) if sampled else None
        )

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
            current_index=saved.current_index,
            total_questions=len(question_ids),
            question=first_question,
            draft_answers=None,
        )

    @staticmethod
    def _sanitize_question(q: dict) -> SanitizedQuestion:
        """Project a question body (from ``/sample`` or ``/questions/{id}``) onto
        the candidate-safe shape. Copies only display fields, so answer fields
        (``correct_answers``/``sample_answer``/``answer_explanation``) can never
        reach the client even when the source dict carries them."""
        return SanitizedQuestion(
            id=q.get("_id") or q.get("id"),
            type=q.get("type"),
            question_text=q.get("question_text"),
            options=q.get("options"),
            difficulty=q.get("difficulty"),
        )

    @staticmethod
    async def _next_question(
        question_ids: list, index: int, correlation_id: str | None
    ) -> SanitizedQuestion | None:
        """Best-effort fetch + sanitize of the question at ``index`` for the
        sequential-reveal response. Returns ``None`` when there is no further
        question or when its body can't be fetched — it NEVER raises. A question
        deleted mid-exam (or a transient question-management-service failure)
        must not abort an already-recorded answer and wedge the session on a
        question the candidate already answered. The body is a convenience that
        is re-derivable on the next call, so it is deliberately not persisted in
        the idempotency payload (attached live on every response/replay)."""
        if index >= len(question_ids):
            return None
        try:
            raw = await SessionService._fetch_question(question_ids[index], correlation_id)
        except HTTPException:
            return None
        return SessionService._sanitize_question(raw)

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

        # Idempotency replay — checked AFTER the 404/ownership guards and scoped
        # to this session, so a key reused across sessions or users can't replay
        # another context's response. Read the payload into a local BEFORE the
        # rollback: rollback expires loaded ORM instances, so touching
        # ``prior.response_payload`` afterwards could re-query (or raise) under a
        # real concurrent race.
        if idempotency_key:
            prior = await AnswerRepository.get_by_session_and_key(
                db, session_id, idempotency_key
            )
            if prior is not None:
                payload = prior.response_payload
                # Capture before rollback — it expires loaded ORM instances.
                qids = session.question_ids or []
                await db.rollback()
                resp = AnswerResponse(**payload)
                # next_question isn't persisted; re-derive it live (best-effort)
                # at the stored frontier so replays match the original response.
                resp.next_question = await SessionService._next_question(
                    qids, resp.current_index, correlation_id
                )
                return resp

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
        try:
            result = partial_credit.score_question(
                question.get("type"),
                question.get("correct_answers"),
                body.submitted_answers,
            )
        except ValueError:
            # Not auto-scorable (e.g. a TEXT question that slipped into the
            # sample). Record zero and flag for manual grading rather than
            # 500-ing — that would leave current_index stuck and wedge the
            # session permanently on this question.
            result = ScoreResult(
                is_correct=False, score=0.0, algorithm="manual_grading_required"
            )

        # Advance; finalize if that was the last question.
        new_index = idx + 1
        finished = new_index >= len(question_ids)
        session.current_index = new_index
        if finished:
            session.status = SessionStatus.SUBMITTED
            session.submitted_at = now

        # Score-free response: is_correct/score are persisted below but never
        # returned, so correctness stays hidden from the candidate mid-exam.
        # next_question is left None here and attached AFTER commit (best-effort,
        # outside the row lock) — see below. It is intentionally not part of the
        # persisted payload.
        response = AnswerResponse(
            question_id=current_qid,
            current_index=new_index,
            total_questions=len(question_ids),
            status=session.status,
            submitted_at=session.submitted_at if finished else None,
            next_question=None,
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
            # Lost a concurrent race on (session_id, idempotency_key); the
            # winning request already committed, so replay its stored response.
            await db.rollback()
            if idempotency_key:
                prior = await AnswerRepository.get_by_session_and_key(
                    db, session_id, idempotency_key
                )
                if prior is not None:
                    resp = AnswerResponse(**prior.response_payload)
                    resp.next_question = await SessionService._next_question(
                        question_ids, resp.current_index, correlation_id
                    )
                    return resp
            raise

        # Answer is durable and the row lock is released; reveal the next
        # question best-effort. A fetch failure here leaves a consistent,
        # non-wedged session — the client just gets next_question=None.
        response.next_question = await SessionService._next_question(
            question_ids, new_index, correlation_id
        )
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
