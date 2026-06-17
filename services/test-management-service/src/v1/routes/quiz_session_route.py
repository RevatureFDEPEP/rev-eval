import secrets
from datetime import datetime, timedelta
from statistics import mean
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.db.session import get_db
from src.models.idempotency_key import IdempotencyKey
from src.models.quiz_session import QuizSession, SessionStatus
from src.models.session_answer import SessionAnswer
from src.models.test import Test
from src.models.test_skill import TestSkill
from src.models.test_submission import SubmissionStatus, TestSubmission
from src.schemas.quiz_session_schema import (
    AnswerResponse,
    AnswerSubmit,
    QuizQuestionOut,
    SessionCreate,
    SessionRead,
)
from src.scoring import score_question
from src.utils.dependencies import get_current_user_from_headers
from src.utils.http_client import fetch_question, get_qms_client

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


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    session_id: str,
    body: AnswerSubmit,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_headers),
):
    idempotency_key = request.headers.get("Idempotency-Key", "")[:128] or None
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))

    async with db.begin():
        # Step 2: idempotency early-exit
        if idempotency_key:
            idem_result = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.key == idempotency_key,
                    IdempotencyKey.session_id == session_id,
                )
            )
            cached = idem_result.scalars().first()
            if cached:
                return JSONResponse(content=cached.response_body, status_code=200)

        # Step 3: pessimistic lock on session row
        sess_result = await db.execute(
            select(QuizSession)
            .where(QuizSession.id == session_id)
            .with_for_update()
        )
        session = sess_result.scalars().first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED):
            raise HTTPException(
                status_code=409,
                detail=f"Session is {session.status.value}; no further answers accepted",
            )

        question_ids: list = session.question_ids
        if body.question_id != question_ids[session.current_index]:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Expected question {question_ids[session.current_index]}, "
                    f"got {body.question_id}"
                ),
            )

        # Step 7: fetch question with correct_answers from QMS
        qms = await fetch_question(body.question_id, correlation_id)

        # Step 8: score
        result = score_question(
            qms.get("type", ""),
            qms.get("correct_answers"),
            body.submitted_answers,
        )

        # Step 9: persist answer (immutable)
        answered_index = session.current_index
        db.add(
            SessionAnswer(
                session_id=session_id,
                question_id=body.question_id,
                question_index=answered_index,
                question_type=qms.get("type", ""),
                submitted_answers=body.submitted_answers,
                correct_answers=qms.get("correct_answers"),
                score=result.score,
            )
        )

        # Step 10: advance session
        new_index = answered_index + 1
        is_last = new_index >= len(question_ids)
        session.current_index = new_index
        session.status = SessionStatus.SUBMITTED if is_last else SessionStatus.IN_PROGRESS
        if is_last:
            session.submitted_at = datetime.utcnow()

        # Step 11: finalise submission on last question
        if is_last and session.submission_id:
            sub_result = await db.execute(
                select(TestSubmission)
                .where(TestSubmission.id == session.submission_id)
                .with_for_update()
            )
            submission = sub_result.scalars().first()
            if submission:
                answers_result = await db.execute(
                    select(SessionAnswer).where(SessionAnswer.session_id == session_id)
                )
                answers = answers_result.scalars().all()
                scores = [a.score for a in answers if a.score is not None]
                submission.ai_score = round(mean(scores) * 100) if scores else None
                submission.status = SubmissionStatus.COMPLETED
                submission.submitted_at = session.submitted_at

        # Step 12: fetch next question if not last
        next_q: QuizQuestionOut | None = None
        if not is_last:
            next_qms = await fetch_question(question_ids[new_index], correlation_id)
            next_q = QuizQuestionOut(
                question_id=next_qms["_id"],
                question_text=next_qms["question_text"],
                question_type=next_qms["type"],
                difficulty=next_qms.get("difficulty", "medium"),
                options=next_qms.get("options"),
            )

        # Step 13: build response
        response_body = AnswerResponse(
            session_id=session_id,
            question_id=body.question_id,
            question_index=answered_index,
            score=result.score,
            algorithm=result.algorithm,
            session_status=session.status.value,
            current_index=session.current_index,
            next_question=next_q,
        ).model_dump()

        # Step 14: store idempotency key inside a SAVEPOINT so a concurrent
        # duplicate only rolls back this insert, not the whole transaction.
        if idempotency_key:
            try:
                async with db.begin_nested():
                    db.add(
                        IdempotencyKey(
                            key=idempotency_key,
                            session_id=session_id,
                            response_body=response_body,
                        )
                    )
            except IntegrityError:
                pass  # concurrent duplicate; our response is still valid

    return AnswerResponse(**response_body)
