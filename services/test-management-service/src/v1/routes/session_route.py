from typing import Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.session_schema import AnswerResponse, AnswerSubmit, SessionCreate, SessionStartResponse
from src.services.session_service import SessionService
from src.utils.dependencies import get_current_user_from_headers

router = APIRouter(prefix="/sessions", tags=["Sessions"], redirect_slashes=False)


@router.post("", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: SessionCreate,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new quiz session.

    - Validates the test exists and reads its duration (server-side).
    - Samples question IDs from question-management-service via $sample.
    - Generates session_id (UUID) and session_token (secrets.token_hex).
    - Persists the session (including ordered question_ids) before responding.
    - Returns session metadata and the first question body.
    - The client never computes or stores timing state directly.

    The X-Correlation-Id header, if present, is forwarded to all downstream calls.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot determine user ID from authentication headers",
        )

    correlation_id: Optional[str] = request.headers.get("X-Correlation-Id")

    return await SessionService.start_session(
        db=db,
        test_id=body.test_id,
        user_id=user_id,
        correlation_id=correlation_id,
    )


@router.post(
    "/{session_id}/answer",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_answer(
    session_id: str,
    body: AnswerSubmit,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    """
    Submit an answer for the current question in a session.

    - Acquires a SELECT FOR UPDATE lock on the session row so concurrent
      retries queue rather than race.
    - Accepts an optional **Idempotency-Key** header; duplicate keys return
      the cached prior response without re-scoring.
    - Scores the answer using exact-match or partial-credit logic depending
      on the question type.
    - Advances current_index.  When the last question is answered the session
      status transitions to **SUBMITTED** and no further answers are accepted
      (409 Conflict).
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot determine user ID from authentication headers",
        )

    correlation_id: Optional[str] = request.headers.get("X-Correlation-Id")

    return await SessionService.submit_answer(
        db=db,
        session_id=session_id,
        submitted_answers=body.submitted_answers,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
