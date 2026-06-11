"""
Answer submission and scoring for quiz sessions.

The score → persist → advance steps run in a SINGLE transaction under a
SELECT FOR UPDATE row lock, so concurrent submits queue rather than race and
the answer insert and index advance are atomic. A unique constraint on
(session_id, question_index) is the durable backstop, and Idempotency-Key
deduplication makes a retried request return its original result.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.quiz_session import QuizSessionStatus
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.session_answer_repository import SessionAnswerRepository
from src.schemas.quiz_session_schema import ParticipantQuestion
from src.schemas.session_answer_schema import AnswerResult, AnswerSubmitRequest
from src.scoring import score
from src.services.quiz_session_service import (
    QuizSessionError,
    QuizSessionService,
    _participant_question,
)

logger = logging.getLogger(__name__)


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

        total = len(session.question_ids)

        # 3. Idempotency: a retried request returns its original result, even if
        #    the session has since expired or been submitted (so the FINAL
        #    answer is replayable). This must run before the status guards.
        if idempotency_key:
            cached = await SessionAnswerRepository.find_by_idempotency_key(
                db, session_id, idempotency_key
            )
            if cached is not None:
                return await QuizSessionScoringService._result_for_cached(
                    session, cached, total
                )

        now = datetime.now(UTC).replace(tzinfo=None)

        # 4. Status guards — auto-expire if the timer has run out.
        if session.status == QuizSessionStatus.ACTIVE and session.expires_at <= now:
            session = await QuizSessionRepository.set_status(
                db, session, QuizSessionStatus.EXPIRED
            )

        if session.status == QuizSessionStatus.EXPIRED:
            raise QuizSessionError("Session has expired", status_code=409)

        if session.status == QuizSessionStatus.SUBMITTED:
            raise QuizSessionError("Session is already submitted", status_code=409)

        # 5. Guard against a corrupted current_index.
        if session.current_index >= total:
            raise QuizSessionError(
                "Session question index is out of range", status_code=409
            )

        # 6. Validate question_id matches the frozen question at current_index.
        answered_index = session.current_index
        expected_id = session.question_ids[answered_index]
        if request.question_id != expected_id:
            raise QuizSessionError(
                f"question_id does not match the current question "
                f"(expected {expected_id})",
                status_code=422,
            )

        # 7. Score against the authoritative question body from QMS.
        raw = await QuizSessionService._fetch_question(request.question_id)
        result = score(
            raw.get("type", ""),
            raw.get("correct_answers"),
            request.submitted_answers,
        )

        new_index = answered_index + 1
        is_final = new_index >= total

        # 8. Fetch the next question BEFORE any write, so a QMS failure here
        #    persists nothing and the request is cleanly retryable.
        next_q: ParticipantQuestion | None = None
        if not is_final:
            next_raw = await QuizSessionService._fetch_question(
                session.question_ids[new_index]
            )
            next_q = _participant_question(next_raw, new_index)

        # 9. Persist the answer and advance the session in ONE transaction. The
        #    unique (session_id, question_index) constraint rejects a concurrent
        #    or keyless double-submit with a 409 instead of double-scoring.
        session.current_index = new_index
        if is_final:
            session.status = QuizSessionStatus.SUBMITTED
            session.submitted_at = now
        stored = SessionAnswerRepository.add(
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
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise QuizSessionError(
                "An answer for this question has already been submitted",
                status_code=409,
            ) from e
        await db.refresh(stored)

        logger.info(
            "answer scored: session_id=%s index=%d is_correct=%s points=%.4f final=%s",
            session_id,
            answered_index,
            result.is_correct,
            result.points_earned,
            is_final,
        )

        return _build_result_from_answer(
            stored,
            session.status,
            new_index,
            total,
            next_q,
            now if is_final else None,
        )

    @staticmethod
    async def _result_for_cached(session, cached, total: int) -> AnswerResult:
        """Rebuild the response for a replayed (idempotent) request from the
        state as of the stored answer, not the session's live position."""
        next_index = cached.question_index + 1
        next_q: ParticipantQuestion | None = None
        if next_index < total:
            raw = await QuizSessionService._fetch_question(
                session.question_ids[next_index]
            )
            next_q = _participant_question(raw, next_index)
        return _build_result_from_answer(
            cached,
            session.status,
            next_index,
            total,
            next_q,
            session.submitted_at,
        )
