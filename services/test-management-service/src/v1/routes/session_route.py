from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.session_schema import SessionCreate, SessionStartResponse
from src.services.session_service import SessionService
from src.utils.dependencies import get_current_user_from_headers

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
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
    - Persists the session before responding.
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
