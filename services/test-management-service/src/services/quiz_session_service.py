import logging
import os
import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.quiz_session import QuizSession, QuizSessionQuestion, SessionStatus
from src.repositories.quiz_session_repository import QuizSessionRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.quiz_session_schema import (
    QuizQuestionOut,
    QuizSessionCreate,
    QuizSessionStartResponse,
)

logger = logging.getLogger(__name__)

_QUESTION_SERVICE_URL = os.getenv(
    "QUESTION_SERVICE_URL", "http://question-management-service:8003"
)
_DEFAULT_DURATION = timedelta(hours=1)

# Coarse anti-abuse guard: maximum concurrent in-progress sessions per user.
# Not a substitute for real rate limiting, but bounds row/HTTP-call exhaustion
# from a single authenticated participant without breaking the normal flow.
_MAX_ACTIVE_SESSIONS_PER_USER = 25

# Question fields that must never reach the participant. The full question
# (including these) is persisted in quiz_session_questions.snapshot_json for
# server-authoritative scoring, so the snapshot is sensitive and must never be
# serialized to a client. The participant-facing payload is built exclusively
# through _strip_correct_answers / QuizQuestionOut.
_SENSITIVE_QUESTION_FIELDS = ("correct_answers", "answer_explanation", "sample_answer")


def _strip_correct_answers(question: Dict[str, Any]) -> QuizQuestionOut:
    """Return question fields safe to send to participant — no answers included."""
    return QuizQuestionOut(
        question_id=question.get("_id") or question.get("id", ""),
        question_type=question.get("type", ""),
        question_text=question.get("question_text", ""),
        options=question.get("options"),
    )


def compute_expires_at(server_now: datetime, duration) -> datetime:
    """Compute session expiry from test.duration (timedelta) or the default."""
    if duration is not None:
        return server_now + duration
    return server_now + _DEFAULT_DURATION


async def _fetch_questions(
    n: int, correlation_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    if correlation_id:
        headers["X-Correlation-Id"] = correlation_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use the list-all endpoint: /questions/filter rejects requests that
            # supply no filter criterion (type/skill/difficulty/tags) with a 400.
            response = await client.get(
                f"{_QUESTION_SERVICE_URL}/v1/api/questions/",
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.error("question-management-service unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="question-management-service is unreachable",
        )

    if response.status_code != 200:
        logger.error(
            "question-management-service returned %d: %s",
            response.status_code,
            response.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"question-management-service returned {response.status_code}",
        )

    pool: List[Dict[str, Any]] = response.json()
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question pool is empty — cannot create quiz session",
        )

    if len(pool) >= n:
        return random.sample(pool, n)
    return pool


class QuizSessionService:

    @staticmethod
    async def create_session(
        db: AsyncSession,
        payload: QuizSessionCreate,
        current_user: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> QuizSessionStartResponse:
        user_id = current_user["id"]

        test = await TestRepository.get_by_id(db, payload.test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {payload.test_id} not found",
            )

        # Authorization: only active tests can be started.
        if not test.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test is not active",
            )

        # IDOR guard: a supplied submission must belong to this user and test.
        if payload.submission_id is not None:
            submission = await TestSubmissionRepository.get_by_id(
                db, payload.submission_id
            )
            if submission is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Submission {payload.submission_id} not found",
                )
            if submission.user_id != user_id or submission.test_id != payload.test_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Submission does not belong to this user and test",
                )

        # Coarse anti-abuse guard against session-creation spam.
        active_count = await QuizSessionRepository.count_active_for_user(db, user_id)
        if active_count >= _MAX_ACTIVE_SESSIONS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many active quiz sessions; finish or abandon one first",
            )

        n_questions = test.number_of_questions or 20
        questions = await _fetch_questions(n_questions, correlation_id)

        server_now = datetime.now(timezone.utc)
        expires_at = compute_expires_at(server_now, test.duration)

        session = QuizSession(
            session_id=uuid.uuid4(),
            test_id=payload.test_id,
            submission_id=payload.submission_id,
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            status=SessionStatus.in_progress,
            current_index=0,
            server_started_at=server_now,
            expires_at=expires_at,
            created_at=server_now,
            updated_at=server_now,
        )

        await QuizSessionRepository.create(db, session)

        for idx, q in enumerate(questions):
            snapshot = QuizSessionQuestion(
                quiz_session_id=session.id,
                question_id=q.get("_id") or q.get("id", ""),
                question_index=idx,
                question_type=q.get("type", ""),
                snapshot_json=q,
            )
            await QuizSessionRepository.add_question(db, snapshot)

        await db.commit()
        await db.refresh(session)

        logger.info(
            "quiz session created",
            extra={
                "session_id": str(session.session_id),
                "test_id": payload.test_id,
                "user_id": current_user["id"],
                "expires_at": expires_at.isoformat(),
                "question_count": len(questions),
            },
        )

        return QuizSessionStartResponse(
            session_id=session.session_id,
            session_token=session.session_token,
            server_now=server_now,
            expires_at=expires_at,
            status=session.status.value,
            current_index=0,
            question=_strip_correct_answers(questions[0]),
        )
