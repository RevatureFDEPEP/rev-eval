"""Route-level tests for POST /v1/api/sessions/{id}/answer (W3-F2).

In-memory SQLite via `get_db`, faked gateway identity, and a fake httpx client
for the question-management-service lookup. SQLite ignores SELECT FOR UPDATE, so
true lock concurrency is deferred to W3-F5; here we cover scoring, index
advance, finalization, idempotency replay, and the 409/403 guard rails.
"""
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.services.session_service as session_service_mod
from src.db.session import Base, get_db
from src.models.answer import QuizAnswer
from src.models.session import QuizSession, SessionStatus
from src.utils.dependencies import get_current_user_from_headers
from src.v1.routes.session_route import router as session_router

# Question bank the fake question-management-service serves, keyed by _id.
# question_text is present so the server can sanitize a fetched body into the
# candidate-facing next_question (SanitizedQuestion requires it).
_QUESTIONS = {
    "q-mcq": {"_id": "q-mcq", "type": "mcq", "question_text": "2+2?", "correct_answers": [2]},
    "q-multi": {"_id": "q-multi", "type": "multi", "question_text": "pick", "correct_answers": [1, 2, 3]},
    "q-tf": {"_id": "q-tf", "type": "true_false", "question_text": "sky blue?", "correct_answers": [True]},
    # Not auto-scorable — graded against a sample answer, no key.
    "q-text": {"_id": "q-text", "type": "text", "question_text": "essay", "sample_answer": "anything"},
}

_USER_ID = 42


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    """Resolves GET /v1/api/questions/{id} from the static bank above."""

    def __init__(self):
        self.calls = []

    async def get(self, url, params=None, headers=None):
        self.calls.append(url)
        qid = url.rstrip("/").rsplit("/", 1)[-1]
        if qid in _QUESTIONS:
            return _FakeResponse(200, _QUESTIONS[qid])
        return _FakeResponse(404, {"detail": "not found"})


@pytest_asyncio.fixture
async def session_factory():
    from src.models.answer import QuizAnswer  # noqa: F401
    from src.models.category import Category  # noqa: F401
    from src.models.category_skill import CategorySkill  # noqa: F401
    from src.models.session import QuizSession  # noqa: F401
    from src.models.skill import Skill  # noqa: F401
    from src.models.test import Test  # noqa: F401
    from src.models.test_skill import TestSkill  # noqa: F401
    from src.models.test_submission import TestSubmission  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _seed_session(
    session_factory,
    *,
    question_ids,
    current_index=0,
    status=SessionStatus.ACTIVE,
    expires_in=timedelta(minutes=30),
    user_id=_USER_ID,
    session_id="sess-1",
) -> str:
    now = datetime.utcnow()
    async with session_factory() as session:
        session.add(
            QuizSession(
                session_id=session_id,
                test_id=1,
                user_id=user_id,
                session_token="t" * 64,
                server_now=now,
                expires_at=now + expires_in,
                status=status,
                current_index=current_index,
                question_ids=question_ids,
            )
        )
        await session.commit()
    return session_id


def _build_client(session_factory):
    app = FastAPI()
    app.include_router(session_router, prefix="/v1/api")

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_user():
        return {"id": _USER_ID, "email": "p@x.io", "role": "PARTICIPANT"}

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_from_headers] = _override_user
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _mock_http(monkeypatch):
    monkeypatch.setattr(session_service_mod, "get_http_client", lambda: _FakeClient())


@pytest.mark.asyncio
async def test_correct_answer_advances_index(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-mcq", "q-tf"])
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [2]}
        )
    assert resp.status_code == 200
    body = resp.json()
    # Response is score-free; forward motion via next_question.
    assert "is_correct" not in body and "score" not in body
    assert body["question_id"] == "q-mcq"
    assert body["current_index"] == 1
    assert body["total_questions"] == 2
    assert body["status"] == "ACTIVE"
    assert body["next_question"]["id"] == "q-tf"
    assert "correct_answers" not in body["next_question"]

    # Scoring still happens server-side and is persisted (just not returned).
    async with session_factory() as session:
        rows = (await session.execute(select(QuizAnswer))).scalars().all()
        assert len(rows) == 1
        assert rows[0].question_id == "q-mcq"
        assert rows[0].question_index == 0
        assert rows[0].is_correct is True
        assert rows[0].score == 1.0


@pytest.mark.asyncio
async def test_partial_credit_multi_scores_jaccard(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-multi", "q-tf"])
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [1, 2]}
        )
    assert resp.status_code == 200
    # Score isn't disclosed in the response; assert it on the persisted row.
    async with session_factory() as session:
        row = (await session.execute(select(QuizAnswer))).scalars().first()
        assert row.is_correct is False
        assert row.score == pytest.approx(2 / 3)
        assert row.algorithm == "partial_credit"


@pytest.mark.asyncio
async def test_final_question_finalizes_session(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-mcq"])
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [2]}
        )
    body = resp.json()
    assert body["status"] == "SUBMITTED"
    assert body["current_index"] == 1
    assert body["next_question"] is None  # nothing left to reveal
    assert body["submitted_at"] is not None

    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.status == SessionStatus.SUBMITTED
        assert row.submitted_at is not None


@pytest.mark.asyncio
async def test_answer_after_submitted_returns_409(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], status=SessionStatus.SUBMITTED
    )
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [2]}
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_expired_session_is_finalized_and_409(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], expires_in=timedelta(minutes=-1)
    )
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [2]}
        )
    assert resp.status_code == 409

    async with session_factory() as session:
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.status == SessionStatus.EXPIRED


@pytest.mark.asyncio
async def test_other_users_session_returns_403(session_factory):
    sid = await _seed_session(
        session_factory, question_ids=["q-mcq"], user_id=999
    )
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer", json={"submitted_answers": [2]}
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_out_of_order_question_id_returns_409(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-mcq", "q-tf"])
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer",
            json={"submitted_answers": [2], "question_id": "q-tf"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_idempotency_key_replays_without_re_advancing(session_factory):
    sid = await _seed_session(session_factory, question_ids=["q-mcq", "q-tf"])
    headers = {"Idempotency-Key": "abc-123"}
    async with _build_client(session_factory) as client:
        first = await client.post(
            f"/v1/api/sessions/{sid}/answer",
            json={"submitted_answers": [2]},
            headers=headers,
        )
        second = await client.post(
            f"/v1/api/sessions/{sid}/answer",
            json={"submitted_answers": [1]},  # different answer, same key
            headers=headers,
        )
    assert first.status_code == 200
    assert second.status_code == 200
    # Replay returns the ORIGINAL response, ignoring the new answer.
    assert second.json() == first.json()
    assert second.json()["current_index"] == 1

    async with session_factory() as session:
        rows = (await session.execute(select(QuizAnswer))).scalars().all()
        assert len(rows) == 1  # scored exactly once
        row = (await session.execute(
            select(QuizSession).where(QuizSession.session_id == sid)
        )).scalars().first()
        assert row.current_index == 1  # advanced once, not twice


@pytest.mark.asyncio
async def test_text_question_scores_zero_and_advances_not_500(session_factory):
    """A non-auto-scorable TEXT question must not 500 or wedge the session:
    record zero, flag manual grading, and advance current_index."""
    sid = await _seed_session(session_factory, question_ids=["q-text", "q-tf"])
    async with _build_client(session_factory) as client:
        resp = await client.post(
            f"/v1/api/sessions/{sid}/answer",
            json={"submitted_answers": ["my essay"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_index"] == 1  # advanced — not stuck on the text question
    assert body["status"] == "ACTIVE"
    assert body["next_question"]["id"] == "q-tf"
    # Manual-grading fallback is recorded server-side, not surfaced.
    async with session_factory() as session:
        row = (await session.execute(select(QuizAnswer))).scalars().first()
        assert row.is_correct is False
        assert row.score == 0.0
        assert row.algorithm == "manual_grading_required"


@pytest.mark.asyncio
async def test_idempotency_key_is_scoped_per_session(session_factory):
    """The same Idempotency-Key on a DIFFERENT session must not replay the
    first session's response — each session scores its own answer."""
    sid_a = await _seed_session(
        session_factory, question_ids=["q-mcq"], session_id="sess-a"
    )
    sid_b = await _seed_session(
        session_factory, question_ids=["q-tf"], session_id="sess-b"
    )
    headers = {"Idempotency-Key": "shared-key"}
    async with _build_client(session_factory) as client:
        a = await client.post(
            f"/v1/api/sessions/{sid_a}/answer",
            json={"submitted_answers": [2]},
            headers=headers,
        )
        b = await client.post(
            f"/v1/api/sessions/{sid_b}/answer",
            json={"submitted_answers": [True]},
            headers=headers,
        )
    assert a.status_code == 200 and b.status_code == 200
    # Session B was scored independently, NOT replayed from A.
    assert b.json()["status"] == "SUBMITTED"  # q-tf was B's only question
    assert b.json()["next_question"] is None

    async with session_factory() as session:
        rows = (await session.execute(select(QuizAnswer))).scalars().all()
        assert len(rows) == 2  # one row per session, key not collided
