"""
Session service for test-management-service.

Responsibilities:
- Validate the requested test exists and extract its duration.
- Sample question IDs from question-management-service via $sample aggregation.
- Generate server-authoritative session_id, session_token, server_now, expires_at.
- Persist the session row before responding.
- Propagate X-Correlation-Id to all outbound httpx calls.
"""
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.session_repository import SessionRepository
from src.repositories.test_repository import TestRepository
from src.schemas.session_schema import SessionStartResponse
from src.utils.http_client import get_http_client

_QUESTION_SERVICE_URL = os.getenv("QUESTION_SERVICE_URL", "http://question-management-service:8003")
_DEFAULT_DURATION_SECONDS = 7200  # 2-hour fallback when test.duration is not set


class SessionService:

    @staticmethod
    async def start_session(
        db: AsyncSession,
        test_id: int,
        user_id: int,
        correlation_id: Optional[str] = None,
    ) -> SessionStartResponse:
        """
        Create a new quiz session.

        1. Fetch the test (validates existence + gets duration).
        2. Sample question IDs from question-management-service.
        3. Fetch first question body.
        4. Persist the session row.
        5. Return the response — the client never computes timing state.
        """
        # ── 1. Resolve test ──────────────────────────────────────────────────
        test = await TestRepository.get_by_id(db, test_id)
        if test is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test {test_id} not found",
            )

        question_count: int = test.number_of_questions or 20
        duration_seconds: int = (
            int(test.duration.total_seconds()) if test.duration else _DEFAULT_DURATION_SECONDS
        )

        # ── 2. Sample question IDs via $sample ───────────────────────────────
        outbound_headers: Dict[str, str] = {}
        if correlation_id:
            outbound_headers["X-Correlation-Id"] = correlation_id

        client: httpx.AsyncClient = get_http_client()
        try:
            sample_resp = await client.get(
                f"{_QUESTION_SERVICE_URL}/v1/api/questions/random",
                params={"count": question_count},
                headers=outbound_headers,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach question-management-service: {exc}",
            )

        if sample_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"question-management-service returned {sample_resp.status_code}",
            )

        sampled_questions: list = sample_resp.json()
        question_ids = [q["_id"] for q in sampled_questions if "_id" in q]

        # ── 3. Fetch first question body ─────────────────────────────────────
        first_question: Optional[Dict[str, Any]] = None
        if question_ids:
            first_id = question_ids[0]
            try:
                q_resp = await client.get(
                    f"{_QUESTION_SERVICE_URL}/v1/api/questions/{first_id}",
                    headers=outbound_headers,
                )
                if q_resp.status_code == 200:
                    first_question = q_resp.json()
            except httpx.RequestError:
                # Non-fatal: session is still created, first_question is null
                pass

        # ── 4. Build server-authoritative timing ────────────────────────────
        server_now = datetime.utcnow()
        expires_at = server_now + timedelta(seconds=duration_seconds)
        session_id = str(uuid.uuid4())
        session_token = secrets.token_hex(32)  # 64-char hex string

        # ── 5. Persist ───────────────────────────────────────────────────────
        await SessionRepository.create(
            db,
            session_id=session_id,
            test_id=test_id,
            user_id=user_id,
            session_token=session_token,
            server_now=server_now,
            expires_at=expires_at,
        )

        return SessionStartResponse(
            session_id=session_id,
            session_token=session_token,
            server_now=server_now,
            expires_at=expires_at,
            first_question=first_question,
        )
