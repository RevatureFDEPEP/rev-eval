import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.db.session import get_db
from src.models.quiz_session import QuizSession
from src.models.test import Test
from src.models.test_skill import TestSkill
from src.schemas.quiz_session_schema import QuizQuestionOut, SessionCreate, SessionRead
from src.utils.dependencies import get_current_user_from_headers
from src.utils.http_client import get_qms_client

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
):
    # Fetch test with skills eagerly loaded
    result = await db.execute(
        select(Test)
        .options(selectinload(Test.test_skills).selectinload(TestSkill.skill))
        .where(Test.id == body.test_id)
    )
    test = result.scalars().first()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    # Propagate correlation ID across service boundary
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))

    # Sample questions from question-management-service
    client = get_qms_client()
    skill_names = [ts.skill.name for ts in test.test_skills]
    params: dict = {"n": test.number_of_questions or 20}
    if skill_names:
        params["skills"] = ",".join(skill_names)

    try:
        resp = await client.get(
            "/v1/api/questions/sample",
            params=params,
            headers={"X-Correlation-Id": correlation_id},
        )
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Question service error: {exc}",
        ) from exc

    sampled: list = resp.json()
    if not sampled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No questions available for this test",
        )

    # Compute server-authoritative timing — client never touches this
    server_now = datetime.utcnow()
    duration_secs = test.duration.total_seconds() if test.duration else 3600
    expires_at = server_now + timedelta(seconds=duration_secs)

    session = QuizSession(
        session_token=secrets.token_hex(32),
        test_id=body.test_id,
        submission_id=body.submission_id,
        user_id=current_user["id"],
        question_ids=[q["_id"] for q in sampled],
        server_now=server_now,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    raw_q = sampled[0]
    first_q = QuizQuestionOut(
        question_id=raw_q["_id"],
        question_text=raw_q["question_text"],
        question_type=raw_q["type"],
        difficulty=raw_q.get("difficulty", "medium"),
        options=raw_q.get("options"),
    )

    return SessionRead(
        session_id=session.id,
        session_token=session.session_token,
        test_id=session.test_id,
        user_id=session.user_id,
        status=session.status.value,
        current_index=session.current_index,
        server_now=session.server_now,
        expires_at=session.expires_at,
        first_question=first_q,
    )
