"""Trainer manual-grading flow for free-text answers (W5-F1).

A free-text answer is recorded ``PENDING_REVIEW`` at submit (it can't be
auto-scored). This service lists the to-grade queue and applies a trainer's
manual grade, recomputing the session's ``needs_grading`` flag. The attempt
score itself is computed on-read by the reporting service
(``AVG(answers.score)`` over non-pending rows), so a grade is a plain answer-row
update — no score column to recompute here.
"""
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from src.models.answer import GradingStatus
from src.repositories.answer_repository import AnswerRepository
from src.repositories.session_repository import SessionRepository
from src.schemas.grading_schema import (
    GradedAnswerOut,
    GradingQueueOut,
    PendingAnswerOut,
)
from src.utils import question_client

logger = logging.getLogger(__name__)


class AnswerNotFoundError(Exception):
    """No answer at the given session slot (→ 404)."""


class AnswerNotPendingError(Exception):
    """The answer is not awaiting manual review (→ 409)."""


class GradingService:
    @staticmethod
    async def list_queue(
        db: AsyncSession, *, test_id=None, page: int = 1, size: int = 20
    ) -> GradingQueueOut:
        """Trainer to-grade queue: PENDING_REVIEW answers, enriched with each
        question's prompt + sample answer from question-management-service."""
        rows, total = await AnswerRepository.list_pending(
            db, test_id=test_id, page=page, size=size
        )
        items = []
        for answer, user_id, t_id, submitted_at, test_name in rows:
            question_text = sample_answer = None
            try:
                q = await question_client.get_question(answer.question_id)
                question_text = q.get("question_text")
                sample_answer = q.get("sample_answer")
            except Exception:  # noqa: BLE001 — enrichment is best-effort
                logger.warning(
                    "grading queue: question fetch failed for %s", answer.question_id
                )
            items.append(
                PendingAnswerOut(
                    answer_id=answer.id,
                    session_id=answer.session_id,
                    user_id=user_id,
                    question_index=answer.question_index,
                    question_id=answer.question_id,
                    submitted_answers=answer.submitted_answers,
                    submitted_at=submitted_at,
                    test_id=t_id,
                    test_name=test_name,
                    question_text=question_text,
                    sample_answer=sample_answer,
                )
            )
        return GradingQueueOut(items=items, total=total, page=page, size=size)

    @staticmethod
    async def grade_answer(
        db: AsyncSession,
        session_id: UUID,
        question_index: int,
        score: float,
        feedback,
        grader_id,
    ) -> GradedAnswerOut:
        """Apply a trainer's manual grade to one free-text answer and recompute
        the session's ``needs_grading`` flag. Idempotent re-grading of an
        already-GRADED answer is allowed; auto-scored answers are rejected."""
        answer = await AnswerRepository.get_by_slot(db, session_id, question_index)
        if answer is None:
            raise AnswerNotFoundError("Answer not found")
        if answer.grading_status == GradingStatus.AUTO:
            raise AnswerNotPendingError("Answer is auto-scored, not manually graded")

        answer.score = score
        answer.is_correct = score >= 1.0
        answer.feedback = feedback
        answer.graded_by_id = grader_id
        answer.graded_at = datetime.utcnow()
        answer.grading_status = GradingStatus.GRADED
        await db.flush()

        # Recompute the attempt's provisional flag now this answer is graded.
        session = await SessionRepository.get_for_update(db, session_id)
        remaining = await AnswerRepository.count_pending(db, session_id)
        session.needs_grading = remaining > 0
        await SessionRepository.flush(db, session)
        await db.commit()

        return GradedAnswerOut(
            answer_id=answer.id,
            session_id=answer.session_id,
            question_index=answer.question_index,
            score=answer.score,
            is_correct=answer.is_correct,
            grading_status=answer.grading_status.value,
            feedback=answer.feedback,
            graded_by_id=answer.graded_by_id,
            graded_at=answer.graded_at,
            session_needs_grading=session.needs_grading,
        )
