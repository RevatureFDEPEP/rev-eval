from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.session_schema import SessionCreate, SessionOut
from src.services.session_service import EmptyQuestionBankError, SessionService
from src.utils.dependencies import get_current_user_from_headers
from src.utils.question_client import QuestionServiceError

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: SessionCreate,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Start a quiz session: mint an opaque token, record server-authoritative
    timing, sample the question set from question-management-service, and
    return the first (sanitized) question."""
    user_id = current_user.get("id")
    try:
        return await SessionService.create_session(db, session_in.test_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found") from None
    except EmptyQuestionBankError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from None
    except QuestionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"question-management-service unavailable: {e}",
        ) from None
