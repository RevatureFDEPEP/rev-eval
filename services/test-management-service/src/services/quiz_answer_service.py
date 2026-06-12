import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.idempotency_key import IdempotencyKey
from src.models.quiz_answer import QuizAnswer
from src.models.quiz_session import SessionStatus
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.quiz_answer_repository import QuizAnswerRepository
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.schemas.quiz_session_schema import AnswerAck, AnswerSubmit
from src.scoring import score_question
from src.services.quiz_session_service import _strip_correct_answers

logger = logging.getLogger(__name__)


def _request_hash(payload: AnswerSubmit) -> str:
    """Stable hash of the request body (answer order does not matter)."""
    canonical = json.dumps(
        {
            "question_id": payload.question_id,
            "answers": sorted(payload.answers, key=lambda a: (type(a).__name__, str(a))),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _aware(dt: datetime) -> datetime:
    """Treat naive timestamps from the DB as UTC for safe comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _session_tokens_match(expected: str, submitted: str) -> bool:
    """Compare token bytes so malformed Unicode input still rejects cleanly."""
    return hmac.compare_digest(
        expected.encode("utf-8"),
        submitted.encode("utf-8"),
    )


class QuizAnswerService:

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        session_id,
        payload: AnswerSubmit,
        idempotency_key: str,
        current_user: Dict[str, Any],
    ) -> AnswerAck:
        # Lock the session row for the duration of the transaction so concurrent
        # submissions for the same session serialize rather than race.
        session = await QuizSessionRepository.get_for_update(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz session not found",
            )

        # Authorization: the caller must own the session and present the token.
        if session.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to this user",
            )
        if not _session_tokens_match(session.session_token, payload.session_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid session token",
            )

        # Idempotency: replay an identical request, reject key reuse with a
        # different body. Checked before any state mutation.
        request_hash = _request_hash(payload)
        existing = await IdempotencyRepository.get(db, session.id, idempotency_key)
        if existing is not None:
            if existing.request_hash == request_hash:
                return AnswerAck(**existing.response_json)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key reused with a different request body",
            )

        # State machine: terminal sessions reject mutations.
        if session.status in (SessionStatus.submitted, SessionStatus.expired):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session is {session.status.value}; no further answers accepted",
            )

        now = datetime.now(timezone.utc)
        if _aware(session.expires_at) <= now:
            session.status = SessionStatus.expired
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has expired",
            )

        # Locate the submitted question within this session's snapshot set.
        questions = await QuizSessionRepository.get_questions_for_session(db, session.id)
        snapshot = next(
            (q for q in questions if q.question_id == payload.question_id), None
        )
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Question does not belong to this session",
            )

        # Server-authoritative ordering: answers must arrive for the current
        # question. Out-of-order / already-answered submissions are conflicts.
        if snapshot.question_index != session.current_index:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Expected answer for question index {session.current_index}, "
                    f"got {snapshot.question_index}"
                ),
            )

        # Defense-in-depth: if a scored answer already exists for this index
        # (e.g. row lock not honored on a non-Postgres backend), reject with a
        # clean 409 rather than letting the unique constraint raise a 500.
        already = await QuizAnswerRepository.get_by_session_and_index(
            db, session.id, snapshot.question_index
        )
        if already is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Question already answered",
            )

        # Score against the correct answers held in the (server-only) snapshot.
        correct_answers = (snapshot.snapshot_json or {}).get("correct_answers")
        result = score_question(
            snapshot.question_type, correct_answers, payload.answers
        )

        await QuizAnswerRepository.add(
            db,
            QuizAnswer(
                quiz_session_id=session.id,
                question_id=snapshot.question_id,
                question_index=snapshot.question_index,
                submitted_answers=list(payload.answers),
                earned=result.earned,
                possible=result.possible,
                is_correct=result.is_correct,
                created_at=now,
            ),
        )

        # Advance the cursor; finalize the session on the last question.
        session.current_index = snapshot.question_index + 1
        total = len(questions)
        finished = session.current_index >= total

        next_question = None
        if finished:
            session.status = SessionStatus.submitted
            session.submitted_at = now
        else:
            next_snapshot = next(
                (q for q in questions if q.question_index == session.current_index),
                None,
            )
            if next_snapshot is not None:
                next_question = _strip_correct_answers(next_snapshot.snapshot_json)

        ack = AnswerAck(
            question_id=snapshot.question_id,
            recorded=True,
            current_index=session.current_index,
            status=session.status.value,
            finished=finished,
            next_question=next_question,
        )

        # Persist the idempotency record so a retry replays this exact response.
        await IdempotencyRepository.add(
            db,
            IdempotencyKey(
                key=idempotency_key,
                quiz_session_id=session.id,
                request_hash=request_hash,
                response_json=ack.model_dump(mode="json"),
            ),
        )

        await db.commit()

        logger.info(
            "quiz answer recorded",
            extra={
                "session_id": str(session.session_id),
                "user_id": current_user["id"],
                "question_index": snapshot.question_index,
                "current_index": session.current_index,
                "finished": finished,
            },
        )

        return ack
