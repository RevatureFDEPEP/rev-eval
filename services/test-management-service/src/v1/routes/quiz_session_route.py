import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.quiz_session_schema import (
    AnswerResultResponse,
    AnswerSubmit,
    DraftPatch,
    DraftResponse,
    QuizSessionCreate,
    QuizSessionStartResponse,
    QuizSessionStateResponse,
    QuizSubmitResponse,
)
from src.services.quiz_session_service import QuizSessionService
from src.utils.dependencies import get_current_participant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["quiz-sessions"])


@router.post(
    "",
    response_model=QuizSessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quiz session",
    description=(
        "Mint a server-authoritative quiz session. Returns session timing "
        "(server_now/expires_at), an opaque session token, the session id, and "
        "the first question without answer keys."
    ),
)
async def create_quiz_session(
    payload: QuizSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> QuizSessionStartResponse:
    correlation_id = x_correlation_id or x_request_id
    return await QuizSessionService.create_session(
        db, payload, current_user, correlation_id
    )


@router.get(
    "/{session_id}",
    response_model=QuizSessionStateResponse,
    summary="Get quiz session state",
    description=(
        "Return the full session state for resume/refresh: server time, "
        "expiry, current index, buffered draft answers, and all questions "
        "(without answer keys). Overdue sessions are reported as expired."
    ),
)
async def get_quiz_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
) -> QuizSessionStateResponse:
    return await QuizSessionService.get_session(db, session_id, current_user)


@router.patch(
    "/{session_id}/draft",
    response_model=DraftResponse,
    summary="Autosave draft answers",
    description=(
        "Persist buffered answers and/or the current question index to the "
        "durable session. Rejected once the session is submitted or expired."
    ),
)
async def save_draft(
    session_id: str,
    patch: DraftPatch,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
) -> DraftResponse:
    return await QuizSessionService.save_draft(db, session_id, patch, current_user)


@router.post(
    "/{session_id}/answers",
    response_model=AnswerResultResponse,
    summary="Submit and score one answer",
    description=(
        "Score a single answer server-side and record it. Supply an "
        "Idempotency-Key header to make retries safe: the same key with the "
        "same payload replays the stored response; a different payload is a "
        "409 conflict. Rejected once the session is submitted or expired. The "
        "response does not reveal per-question correctness."
    ),
)
async def submit_answer(
    session_id: str,
    payload: AnswerSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> AnswerResultResponse:
    return await QuizSessionService.submit_answer(
        db, session_id, payload, current_user, idempotency_key
    )


@router.post(
    "/{session_id}/submit",
    response_model=QuizSubmitResponse,
    summary="Finalize a quiz session",
    description=(
        "Lock the session and compute the aggregate score from recorded "
        "answers. Idempotent: a finalized session replays its stored tally."
    ),
)
async def submit_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_participant),
) -> QuizSubmitResponse:
    return await QuizSessionService.submit_session(db, session_id, current_user)
