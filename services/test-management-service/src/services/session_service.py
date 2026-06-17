import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.test import TestType
from src.models.test_session import SessionStatus, TestSession
from src.models.test_submission import SubmissionStatus
from src.repositories.session_question_repository import SessionQuestionRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.skill_repository import SkillRepository
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.schemas.session_schema import QuestionOut, SessionResponse
from src.schemas.test_submission_schema import TestSubmissionUpdate
from src.utils.http_client import call_service

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {
    SubmissionStatus.COMPLETED,
    SubmissionStatus.EVALUATED,
    SubmissionStatus.GRADED,
    SubmissionStatus.ABANDONED,
}


async def create_session(
    db: AsyncSession,
    quiz_id: int,
    user_id: int,
    correlation_id: str,
) -> SessionResponse:
    # 1. Validate quiz
    test = await TestRepository.get_by_id(db, quiz_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz {quiz_id} not found")
    if test.test_type != TestType.QUIZ:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Test {quiz_id} is not a QUIZ type")
    if not test.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Quiz {quiz_id} is not active")

    # 2. Find participant submission
    submission = await TestSubmissionRepository.get_by_user_and_test(db, user_id, quiz_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No submission found for user {user_id} on quiz {quiz_id}",
        )
    if submission.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submission is in terminal status '{submission.status}'; cannot create session",
        )

    # 3. Idempotency — return existing ACTIVE non-expired session if one exists
    existing = await SessionRepository.get_by_submission_id(db, submission.id)
    if existing:
        if existing.status == SessionStatus.ACTIVE and existing.expires_at > datetime.utcnow():
            sq = await SessionQuestionRepository.list_by_session(db, existing.id)
            first_question = await _fetch_question(existing.first_question_id, correlation_id)
            return SessionResponse(
                session_token=existing.token,
                submission_id=existing.submission_id,
                test_id=existing.test_id,
                server_now=existing.server_now,
                expires_at=existing.expires_at,
                total_questions=len(sq),
                current_position=existing.current_position,
                first_question=first_question,
            )
        # Expired or non-active — mark EXPIRED so a fresh session can be minted
        if existing.status == SessionStatus.ACTIVE:
            existing.status = SessionStatus.EXPIRED
            await db.commit()

    # 4. Mint token and compute timestamps (server-side only)
    token = str(uuid.uuid4())
    server_now = datetime.utcnow()
    expires_at = server_now + (test.duration if test.duration else timedelta(hours=1))

    # 5. Sample question set from question-service before writing to DB
    question_count = test.number_of_questions or 20
    skill_name = await _resolve_first_skill(db, quiz_id)
    question_ids, first_question = await _sample_questions(question_count, skill_name, correlation_id)

    # 6. Persist session + question list in one transaction
    first_question_id = question_ids[0] if question_ids else None
    session_obj = TestSession(
        token=token,
        submission_id=submission.id,
        test_id=quiz_id,
        user_id=user_id,
        first_question_id=first_question_id,
        server_now=server_now,
        expires_at=expires_at,
        status=SessionStatus.ACTIVE,
        current_position=0,
    )
    db.add(session_obj)
    await db.flush()  # get session_obj.id without committing

    if question_ids:
        await SessionQuestionRepository.bulk_create(db, session_obj.id, question_ids)

    await db.commit()
    await db.refresh(session_obj)

    # 7. Transition submission to IN_PROGRESS
    if submission.status == SubmissionStatus.ASSIGNED:
        await TestSubmissionRepository.update(
            db,
            submission,
            TestSubmissionUpdate(status=SubmissionStatus.IN_PROGRESS, started_at=server_now),
        )

    return SessionResponse(
        session_token=session_obj.token,
        submission_id=session_obj.submission_id,
        test_id=session_obj.test_id,
        server_now=session_obj.server_now,
        expires_at=session_obj.expires_at,
        total_questions=len(question_ids),
        current_position=0,
        first_question=first_question,
    )


async def _resolve_first_skill(db: AsyncSession, test_id: int) -> str | None:
    links = await TestSkillRepository.list_by_test(db, test_id)
    if not links:
        return None
    skill = await SkillRepository.get_by_id(db, links[0].skill_id)
    return skill.name if skill else None


async def _sample_questions(
    count: int,
    skill_name: str | None,
    correlation_id: str,
) -> tuple[list[str], QuestionOut | None]:
    """
    Call /sample on question-service and return (question_id_list, first_QuestionOut).
    Returns ([], None) on degradation — session is still created without questions.
    """
    try:
        params = f"count={count}"
        if skill_name:
            params += f"&skill={quote(skill_name, safe='')}"
        url = f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/sample?{params}"

        response = await call_service(url, correlation_id=correlation_id)

        if response.status_code == 200:
            questions = response.json()
            if questions:
                ids = [str(q.get("id") or q.get("_id")) for q in questions]
                q = questions[0]
                first = QuestionOut(
                    id=ids[0],
                    type=q.get("type", ""),
                    question_text=q.get("question_text", ""),
                    options=q.get("options"),
                    difficulty=q.get("difficulty"),
                    skills=q.get("skills", []),
                    tags=q.get("tags", []),
                )
                return ids, first
    except (httpx.ConnectError, httpx.NetworkError) as exc:
        logger.warning("[%s] Question-service unavailable: %s", correlation_id, exc)
    except Exception as exc:
        logger.warning("[%s] Unexpected error sampling questions: %s", correlation_id, exc)

    return [], None


async def _fetch_question(question_id: str | None, correlation_id: str) -> QuestionOut | None:
    """Re-fetch a specific question by ID (used for idempotent session return)."""
    if not question_id:
        return None
    try:
        url = f"{settings.QUESTION_SERVICE_URL}/v1/api/questions/{question_id}"
        response = await call_service(url, correlation_id=correlation_id)
        if response.status_code == 200:
            q = response.json()
            return QuestionOut(
                id=str(q.get("id") or q.get("_id")),
                type=q.get("type", ""),
                question_text=q.get("question_text", ""),
                options=q.get("options"),
                difficulty=q.get("difficulty"),
                skills=q.get("skills", []),
                tags=q.get("tags", []),
            )
    except Exception as exc:
        logger.warning("[%s] Could not re-fetch question %s: %s", correlation_id, question_id, exc)
    return None
