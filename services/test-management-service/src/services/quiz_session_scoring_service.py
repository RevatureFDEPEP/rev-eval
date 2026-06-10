"""
Answer submission and scoring for quiz sessions.

Wraps the read-modify-write in a SELECT FOR UPDATE transaction so concurrent
retries queue rather than race. Idempotency-Key deduplication prevents
double-scoring on retried requests.
"""

import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.quiz_session import QuizSessionStatus
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.session_answer_repository import SessionAnswerRepository
from src.schemas.quiz_session_schema import ParticipantQuestion
from src.schemas.session_answer_schema import AnswerResult, AnswerSubmitRequest
from src.scoring import score
from src.services.quiz_session_service import QuizSessionError, _participant_question
from src.utils.logging_config import get_correlation_id
from src.utils.question_client import get_question_client

logger = logging.getLogger(__name__)


async def _fetch_question(question_id: str) -> dict:
    """Fetch a single full question payload from question-management-service."""
    from src.config.settings import settings

    url = f"{settings.QUESTION_MANAGEMENT_SERVICE_URL}/v1/api/questions/{question_id}"
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
            "Could not load question from question-management-service",
            status_code=502,
        )
    return response.json()


def _build_result_from_answer(
    stored, session_status, current_index, total_questions, next_question, submitted_at
) -> AnswerResult:
    return AnswerResult(
        question_id=stored.question_id,
        question_index=stored.question_index,
        is_correct=stored.is_correct,
        points_earned=stored.points_earned,
        max_points=stored.max_points,
        requires_manual_review=stored.requires_manual_review,
        session_status=session_status,
        current_index=current_index,
        total_questions=total_questions,
        question=next_question,
        submitted_at=submitted_at,
    )


class QuizSessionScoringService:
    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id: str,
        user_id: int,
        request: AnswerSubmitRequest,
        idempotency_key: str | None,
    ) -> AnswerResult:
        # 1. Lock session row for update (no-op on SQLite; row-lock on Postgres).
        session = await QuizSessionRepository.lock_for_update(db, session_id)
        if session is None:
            raise ValueError("Session not found")

        # 2. Ownership check.
        if session.user_id != user_id:
            raise QuizSessionError("Not authorized for this session", status_code=403)

        now = datetime.now(UTC).replace(tzinfo=None)

        # 3. Status guards — auto-expire if timer has run out.
        if session.status == QuizSessionStatus.ACTIVE and session.expires_at <= now:
            session = await QuizSessionRepository.set_status(
                db, session, QuizSessionStatus.EXPIRED
            )

        if session.status == QuizSessionStatus.EXPIRED:
            raise QuizSessionError("Session has expired", status_code=409)

        if session.status == QuizSessionStatus.SUBMITTED:
            raise QuizSessionError("Session is already submitted", status_code=409)

        total = len(session.question_ids)

        # 4. Idempotency: return cached result if key already seen.
        if idempotency_key:
            cached = await SessionAnswerRepository.find_by_idempotency_key(
                db, session_id, idempotency_key
            )
            if cached is not None:
                next_q: ParticipantQuestion | None = None
                if session.current_index < total:
                    raw = await _fetch_question(
                        session.question_ids[session.current_index]
                    )
                    next_q = _participant_question(raw, session.current_index)
                return _build_result_from_answer(
                    cached,
                    session.status,
                    session.current_index,
                    total,
                    next_q,
                    session.submitted_at,
                )

        # 5. Validate question_id matches the frozen question at current_index.
        expected_id = session.question_ids[session.current_index]
        if request.question_id != expected_id:
            raise QuizSessionError(
                f"question_id does not match the current question "
                f"(expected {expected_id})",
                status_code=422,
            )

        # 6. Fetch full question from QMS to get correct_answers.
        raw = await _fetch_question(request.question_id)

        # 7. Score.
        result = score(
            raw.get("type", ""),
            raw.get("correct_answers"),
            request.submitted_answers,
        )

        answered_index = session.current_index

        # 8. Persist the scored answer.
        stored = await SessionAnswerRepository.create(
            db,
            session_id=session_id,
            question_id=request.question_id,
            question_index=answered_index,
            submitted_answers=request.submitted_answers,
            is_correct=result.is_correct,
            points_earned=result.points_earned,
            max_points=result.max_points,
            requires_manual_review=result.requires_manual_review,
            idempotency_key=idempotency_key,
        )

        new_index = answered_index + 1

        # 9. Finalize or advance.
        if new_index >= total:
            session = await QuizSessionRepository.set_status(
                db, session, QuizSessionStatus.SUBMITTED
            )
            logger.info(
                "session submitted: session_id=%s user_id=%s", session_id, user_id
            )
            return _build_result_from_answer(
                stored,
                session.status,
                session.current_index,
                total,
                None,
                session.submitted_at,
            )

        session = await QuizSessionRepository.advance_index(db, session, new_index)
        next_raw = await _fetch_question(session.question_ids[new_index])
        next_q = _participant_question(next_raw, new_index)

        logger.info(
            "answer scored: session_id=%s index=%d is_correct=%s points=%.4f",
            session_id,
            answered_index,
            result.is_correct,
            result.points_earned,
        )

        return _build_result_from_answer(
            stored,
            session.status,
            new_index,
            total,
            next_q,
            None,
        )
