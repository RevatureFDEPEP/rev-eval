"""Route tests for ``POST /v1/api/test-sessions/`` (W3-F1, Part B).

SYNC — driven with Starlette's ``TestClient`` (no ``pytest-asyncio`` needed; the
client spins its own event loop to run the async handlers). Every external edge
is overridden so nothing touches the network or a real database:

* ``get_current_user_from_headers`` -> a fake authenticated candidate (and a
  variant that 401s) via ``app.dependency_overrides`` — identity therefore comes
  from the verified gateway claim, exactly as in production, never the body.
* ``get_db`` -> a **mocked async session** (``_FakeSession``). It needs NO real
  DB driver: no ``aiosqlite``, no ``create_async_engine``, nothing to install
  beyond ``requirements.txt``. CI installs ONLY ``requirements.txt`` +
  pytest/pytest-cov/ruff, so a test that built a ``sqlite+aiosqlite`` engine
  would ``ModuleNotFoundError`` at collection — this rewrite removes that edge.
* the qms ``httpx`` client (``get_qms_client``) -> a fake whose ``.get`` returns
  a canned sample list (or raises / returns an error status) — the upstream HTTP
  call is mocked, never made.

Why the session is *faked*, not a real in-memory engine: the route only touches
the session through ``execute``/``add``/``commit``/``refresh``/``rollback``. A
hand-rolled fake replays exactly those, so the route's branches (Test found vs
404, skills filter, persist OK vs SQLAlchemyError rollback) are all driven
without a driver. The one subtlety the fake handles is the PK: ``QuizSession.id``
is a ``Column(default=lambda: uuid4().hex)`` whose default fires only at
flush/INSERT — with no real flush, ``session.id`` would stay ``None`` and the
response would carry ``"None"``. ``_FakeSession.refresh`` populates ``obj.id``
the same way a real flush-then-refresh would, so ``session_id`` is a real,
non-null opaque id. (No production code change is needed — the model's id-timing
is correct against a real DB; the fake just stands in for the flush.)

Coverage of the answer-key contract: the sample list deliberately carries
``correct_answers``/``sample_answer`` and the test asserts they never appear in
the response (the ``QuizQuestionOut`` projection drops them).
"""

import uuid
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.exc import SQLAlchemyError
from src.db.session import get_db
from src.services.quiz_session_helpers import hash_session_token
from src.utils import http_client
from src.utils.dependencies import get_current_user_from_headers

# A candidate identity as the gateway would resolve it (id is the DB PK).
FAKE_USER = {"id": 42, "email": "candidate@example.com", "role": "PARTICIPANT"}

# A canned qms /sample payload. It intentionally CARRIES the answer key so the
# test proves the response projection strips it.
SAMPLE_QUESTIONS = [
    {
        "_id": "q-alpha",
        "question_text": "What is 2 + 2?",
        "type": "mcq",
        "difficulty": "easy",
        "options": [{"option_id": 1, "text": "3"}, {"option_id": 2, "text": "4"}],
        "correct_answers": [2],
        "sample_answer": "4",
    },
    {
        "_id": "q-beta",
        "question_text": "Pick the prime numbers.",
        "type": "multi",
        "difficulty": "medium",
        "options": [{"option_id": 1, "text": "2"}, {"option_id": 2, "text": "4"}],
        "correct_answers": [1],
    },
]


# ---------------------------------------------------------------------------
# Fakes for the DB session (no real driver, no engine)
# ---------------------------------------------------------------------------
class _FakeTest:
    """Stand-in for the ``Test`` ORM row the route reads.

    Only the attributes the route actually reads are present: ``id``,
    ``duration`` (a ``timedelta`` or ``None``), and ``number_of_questions``.
    ``test_skills`` is included so the shape mirrors the ORM model even though
    the route resolves skills via a separate ``execute`` (the join query), not
    by walking this relationship.
    """

    def __init__(
        self,
        *,
        id=1,
        duration: timedelta | None = None,
        number_of_questions: int | None = 2,
        test_skills=(),
    ):
        self.id = id
        self.duration = duration
        self.number_of_questions = number_of_questions
        self.test_skills = list(test_skills)


class _FakeSubmission:
    """Stand-in for a TestSubmission row linked to a candidate/test."""

    def __init__(self, *, id=100, test_id=1, user_id=42):
        self.id = id
        self.test_id = test_id
        self.user_id = user_id


class _FakeActiveQuizSession:
    """Stand-in for an existing in_progress, non-expired ``QuizSession`` row.

    Returned by the idempotency lookup to drive the 409 branch. Only ``id`` is
    read (it isn't, by the route — the route only checks existence), but it's
    carried so the shape mirrors a real row.
    """

    def __init__(self, *, id="existing-session-hex", status="in_progress"):
        self.id = id
        self.status = status


class _ScalarResult:
    """What ``db.execute(select(Test)...)`` returns: ``.scalars().first()``."""

    def __init__(self, first):
        self._first = first

    def scalars(self):
        return self

    def first(self):
        return self._first


class _RowsResult:
    """What ``db.execute(select(Skill.name).join(...))`` returns: ``.all()``
    yielding 1-tuple rows, exactly like a real ``Result`` over a single column."""

    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    """Mocked ``AsyncSession``.

    ``execute`` replays a scripted sequence of results, in the exact order the
    route issues them: the Test lookup, an optional submission lookup, the
    *active-session* idempotency lookup (``select(QuizSession)...`` -> 409 when
    a row comes back), then the skills join. ``add`` records the object;
    ``commit`` is a no-op (or raises, to drive the rollback path); ``refresh``
    populates the PK the way a real flush-then-refresh would; ``rollback``
    records that it was awaited.

    ``active_session`` defaults to ``None`` (the happy path: no existing active
    session). Pass a fake in_progress row to drive the 409 branch.
    """

    _NO_SUBMISSION_LOOKUP = object()

    def __init__(
        self,
        *,
        test,
        skill_rows,
        submission=_NO_SUBMISSION_LOOKUP,
        active_session=None,
        commit_error: Exception | None = None,
    ):
        self._results = [_ScalarResult(test)]
        if submission is not self._NO_SUBMISSION_LOOKUP:
            self._results.append(_ScalarResult(submission))
        # The route runs the active-session idempotency lookup after the Test
        # (and optional submission) check and before the skills join.
        self._results.append(_ScalarResult(active_session))
        self._results.append(_RowsResult(skill_rows))
        self._commit_error = commit_error
        self.added: list = []
        self.committed = False
        self.refreshed: list = []
        self.rolled_back = False

    async def execute(self, *args, **kwargs):
        # Pop in order; if the route ever issues a 3rd query, fail loud.
        if not self._results:  # pragma: no cover - defensive
            raise AssertionError("unexpected extra db.execute call")
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self._commit_error is not None:
            raise self._commit_error
        self.committed = True

    async def refresh(self, obj):
        # Mirror a real flush+refresh: the ``id`` Column default
        # (``uuid4().hex``) fires at INSERT, so after refresh the row has a PK.
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4().hex
        self.refreshed.append(obj)

    async def rollback(self):
        self.rolled_back = True


# ---------------------------------------------------------------------------
# Fakes for the qms httpx client
# ---------------------------------------------------------------------------
class _FakeResponse:
    """Minimal stand-in for ``httpx.Response`` (status + json())."""

    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeQmsClient:
    """Records the outbound call and replays a scripted response / error."""

    def __init__(self, *, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.calls: list[dict] = []

    async def get(self, url, params=None, headers=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if self._raises is not None:
            raise self._raises
        return self._response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _override_db(session: _FakeSession):
    """Override ``get_db`` to yield a given fake session."""

    async def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db


@pytest.fixture
def fake_session():
    """A fake session seeded with a present Test and one skill ('python').

    ``number_of_questions=2`` and ``duration=None`` drive the asserted qms query
    (``n=2``) and the default expiry. Tests that need a missing Test or a commit
    failure build their own ``_FakeSession`` and call ``_override_db``.
    """
    session = _FakeSession(
        test=_FakeTest(id=1, duration=None, number_of_questions=2),
        skill_rows=[("python",)],
    )
    _override_db(session)
    yield session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def override_user():
    """Override the gateway-identity dependency with a fake candidate."""

    async def _user():
        return FAKE_USER

    app.dependency_overrides[get_current_user_from_headers] = _user
    yield
    app.dependency_overrides.pop(get_current_user_from_headers, None)


@pytest.fixture
def client():
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _patch_qms(monkeypatch, *, response=None, raises=None):
    fake = _FakeQmsClient(response=response, raises=raises)
    monkeypatch.setattr(http_client, "get_qms_client", lambda: fake)
    # The route imported the symbol into its own module namespace.
    import src.v1.routes.quiz_session_route as route_mod

    monkeypatch.setattr(route_mod, "get_qms_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# Happy path -> 201 + SessionRead contract
# ---------------------------------------------------------------------------
def test_create_session_happy_path(client, fake_session, override_user, monkeypatch):
    fake = _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 201
    body = resp.json()

    # --- session identity / token contract ---
    assert body["session_id"]  # opaque id present
    assert body["session_id"] != "None"  # refresh populated a real PK
    # The client receives the RAW token (64 hex chars from secrets.token_hex(32)).
    raw_token = body["session_token"]
    assert len(raw_token) == 64
    int(raw_token, 16)  # raises if not hex

    # --- token hash-at-rest contract ---
    # The DB row stores ONLY the SHA-256 hash, never the raw token; the hash is
    # 64 hex chars and equals sha256(returned raw token). The raw token never
    # appears on the persisted row.
    persisted = fake_session.added[0]
    assert not hasattr(persisted, "session_token")  # raw token is never stored
    assert len(persisted.session_token_hash) == 64
    assert persisted.session_token_hash == hash_session_token(raw_token)
    assert persisted.session_token_hash != raw_token  # hash != raw

    # --- server-authoritative state ---
    assert body["test_id"] == 1
    assert body["user_id"] == 42  # from the verified identity, not the body
    assert body["status"] == "in_progress"
    assert body["current_index"] == 0
    assert body["server_now"] is not None
    assert body["expires_at"] is not None
    assert (
        body["expires_at"] > body["server_now"]
    )  # ISO strings compare chronologically

    # --- the persisted row carries the server-set id (refresh ran) ---
    assert fake_session.committed is True
    assert fake_session.refreshed and fake_session.refreshed[0].id is not None
    assert body["session_id"] == str(fake_session.added[0].id)

    # --- first_question is the quiz-safe projection (NO answer key) ---
    fq = body["first_question"]
    assert fq["question_id"] == "q-alpha"
    assert fq["question_type"] == "mcq"
    assert "correct_answers" not in fq
    assert "sample_answer" not in fq
    assert set(fq) == {
        "question_id",
        "question_text",
        "question_type",
        "difficulty",
        "options",
    }

    # the route called qms /sample with the seeded n + skill filter
    assert fake.calls[0]["url"] == "/v1/api/questions/sample"
    assert fake.calls[0]["params"]["n"] == 2
    assert fake.calls[0]["params"]["skills"] == "python"


def test_create_session_with_valid_submission_id_persists_link(
    client, override_user, monkeypatch
):
    session = _FakeSession(
        test=_FakeTest(id=1, duration=None, number_of_questions=2),
        submission=_FakeSubmission(id=77, test_id=1, user_id=42),
        skill_rows=[("python",)],
    )
    _override_db(session)
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post(
            "/v1/api/test-sessions/", json={"test_id": 1, "submission_id": 77}
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    assert session.added[0].submission_id == 77


def test_create_session_invalid_submission_id_404s_before_qms(
    client, override_user, monkeypatch
):
    session = _FakeSession(
        test=_FakeTest(id=1, duration=None, number_of_questions=2),
        submission=None,
        skill_rows=[("python",)],
    )
    _override_db(session)
    fake = _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post(
            "/v1/api/test-sessions/", json={"test_id": 1, "submission_id": 999}
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Submission not found"
    assert fake.calls == []
    assert session.added == []


# ---------------------------------------------------------------------------
# 409 when an active (in_progress, non-expired) session already exists
# ---------------------------------------------------------------------------
def test_create_session_active_session_exists_409_before_qms(
    client, override_user, monkeypatch
):
    """Anti-re-sampling guard: a candidate with an in_progress, non-expired
    session for this (user, test, submission) cannot re-POST to re-roll the
    sample. The route returns 409 BEFORE any qms call and persists nothing."""
    session = _FakeSession(
        test=_FakeTest(id=1, duration=None, number_of_questions=2),
        skill_rows=[("python",)],
        active_session=_FakeActiveQuizSession(),
    )
    _override_db(session)
    fake = _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409
    assert "active session" in resp.json()["detail"].lower()
    # the guard short-circuits before sampling and before any persist
    assert fake.calls == []
    assert session.added == []


# ---------------------------------------------------------------------------
# 404 when the test does not exist
# ---------------------------------------------------------------------------
def test_create_session_test_missing_404(client, override_user, monkeypatch):
    # Test lookup returns None; the skills query is never reached.
    _override_db(_FakeSession(test=None, skill_rows=[]))
    # qms should never be reached, but patch it so a leak is obvious.
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post("/v1/api/test-sessions/", json={"test_id": 9999})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 502 when qms transport fails or returns 5xx
# ---------------------------------------------------------------------------
def test_create_session_qms_transport_error_502(
    client, fake_session, override_user, monkeypatch
):
    _patch_qms(monkeypatch, raises=httpx.ConnectError("connection refused"))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 502
    assert "unavailable" in resp.json()["detail"].lower()


def test_create_session_qms_5xx_502(client, fake_session, override_user, monkeypatch):
    _patch_qms(monkeypatch, response=_FakeResponse(503, {"detail": "down"}))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# 500 (contract error) when qms returns a 4xx — distinct from a 5xx
# ---------------------------------------------------------------------------
def test_create_session_qms_4xx_is_500_contract_error(
    client, fake_session, override_user, monkeypatch
):
    _patch_qms(monkeypatch, response=_FakeResponse(422, {"detail": "bad request"}))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 500
    assert "contract" in resp.json()["detail"].lower()
    # the upstream body/status must NOT be echoed
    assert "bad request" not in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 500 (contract error) when qms returns 200 with a non-JSON body
# ---------------------------------------------------------------------------
def test_create_session_qms_non_json_body_is_500_contract_error(
    client, fake_session, override_user, monkeypatch
):
    # 200 OK but .json() blows up -> upstream contract drift -> generic 500.
    _patch_qms(
        monkeypatch,
        response=_FakeResponse(200, ValueError("Expecting value: line 1 column 1")),
    )

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 500
    assert "contract" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 422 when the sample comes back empty
# ---------------------------------------------------------------------------
def test_create_session_empty_sample_422(
    client, fake_session, override_user, monkeypatch
):
    _patch_qms(monkeypatch, response=_FakeResponse(200, []))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 422
    assert "no questions" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 401 when identity headers are missing (real dependency, not overridden)
# ---------------------------------------------------------------------------
def test_create_session_missing_identity_401(client, fake_session, monkeypatch):
    # Do NOT override get_current_user_from_headers; with no X-User-* headers the
    # real dependency raises 401 before any qms call.
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})

    assert resp.status_code == 401
    assert "authentication" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 401 when the resolved identity carries no id (defense-in-depth)
# ---------------------------------------------------------------------------
def test_create_session_identity_without_id_401(client, fake_session, monkeypatch):
    """A resolved user record missing the DB PK must not mint a session: the
    route refuses with 401 rather than attribute its session to ``None``."""
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    async def _user_no_id():
        return {"email": "x@example.com", "role": "PARTICIPANT"}

    app.dependency_overrides[get_current_user_from_headers] = _user_no_id
    try:
        resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})
    finally:
        app.dependency_overrides.pop(get_current_user_from_headers, None)

    assert resp.status_code == 401
    assert "user id" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 500 (clean) when the DB commit fails — no str(e) leak + rollback awaited
# ---------------------------------------------------------------------------
def test_create_session_db_error_is_clean_500(client, override_user, monkeypatch):
    """When the persist (add/commit/refresh) raises a ``SQLAlchemyError``, the
    route rolls back and returns a generic 500 — never leaking ``str(e)``.

    The fake session's ``commit`` raises an error carrying secret SQL/value
    detail; we assert that detail never reaches the client and that ``rollback``
    was awaited (the txn was cleaned up before re-raising).
    """
    boom = SQLAlchemyError("INSERT INTO quiz_sessions ... 'leaky-sql-value'")
    session = _FakeSession(
        test=_FakeTest(id=1, duration=None, number_of_questions=2),
        skill_rows=[("python",)],
        commit_error=boom,
    )
    _override_db(session)
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail == "Failed to create quiz session"
    # the raw SQL / leaky value must never reach the client
    assert "leaky-sql-value" not in detail
    assert "INSERT" not in detail
    # the transaction was rolled back before raising
    assert session.rolled_back is True


# ---------------------------------------------------------------------------
# Duration -> expiry math: a timedelta duration widens the window
# ---------------------------------------------------------------------------
def test_create_session_duration_drives_expiry(client, override_user, monkeypatch):
    """A test carrying an explicit ``timedelta`` duration sets the expiry window;
    this exercises the ``resolve_duration_seconds(timedelta)`` branch end-to-end
    (the happy-path test uses ``duration=None`` -> default)."""
    session = _FakeSession(
        test=_FakeTest(id=1, duration=timedelta(minutes=30), number_of_questions=2),
        skill_rows=[("python",)],
    )
    _override_db(session)
    _patch_qms(monkeypatch, response=_FakeResponse(200, SAMPLE_QUESTIONS))

    try:
        resp = client.post("/v1/api/test-sessions/", json={"test_id": 1})
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    body = resp.json()
    assert body["expires_at"] > body["server_now"]


# ---------------------------------------------------------------------------
# http_client singleton (lazy init + idempotent close)
# ---------------------------------------------------------------------------
def test_qms_client_is_lazy_singleton_and_closes():
    """``get_qms_client`` builds one shared ``AsyncClient`` (reused across calls);
    ``close_qms_client`` is idempotent and resets the singleton. No network is
    made — only construction/close, with the base_url/timeouts wired."""
    import asyncio

    import httpx as _httpx

    # start clean
    asyncio.run(http_client.close_qms_client())

    c1 = http_client.get_qms_client()
    c2 = http_client.get_qms_client()
    assert c1 is c2  # same singleton reused (shared pool)
    assert isinstance(c1, _httpx.AsyncClient)

    asyncio.run(http_client.close_qms_client())
    # idempotent: a second close on an already-closed/None client is a no-op
    asyncio.run(http_client.close_qms_client())

    # after close, a fresh client is minted
    c3 = http_client.get_qms_client()
    assert c3 is not c1
    asyncio.run(http_client.close_qms_client())


# ===========================================================================
# POST /v1/api/test-sessions/{session_id}/answer  (W3-F2)
# ===========================================================================

import src.v1.routes.quiz_session_route as _answer_route_mod
from src.models.answer import Answer
from src.models.quiz_session import QuizSession


class _AnswerScalarResult:
    """``db.execute(...).scalars().first()`` for the answer flow."""

    def __init__(self, first):
        self._first = first

    def scalars(self):
        return self

    def first(self):
        return self._first


class _AnswerSession:
    """Mocked ``AsyncSession`` for ``submit_answer``.

    Replays the scripted ``execute`` results in the exact order the route issues
    them:

    1. the ``select(QuizSession).where(id==...).with_for_update()`` row lock,
    2. (only when an ``Idempotency-Key`` header is present) the prior-answer
       lookup,

    and then the route scores + persists (``add``/``commit``/``refresh``). The
    fake never needs a real driver: ``with_for_update`` is a no-op here, and the
    QuizSession stand-in is mutated in place so ``current_index``/``status``
    changes are observable after the call.
    """

    def __init__(
        self,
        *,
        quiz_session,
        prior_answer=None,
        with_idempotency=False,
        commit_error: Exception | None = None,
        post_commit_results: list | None = None,
    ):
        self.quiz_session = quiz_session
        self._results = [_AnswerScalarResult(quiz_session)]
        if with_idempotency:
            self._results.append(_AnswerScalarResult(prior_answer))
        # Extra scripted ``execute`` results consumed AFTER the persist commit
        # fails — i.e. the ``_existing_answer`` lookups and the ``fresh``
        # QuizSession re-read on the IntegrityError recovery path. Empty for the
        # happy/clean-500 paths (those never re-query post-commit).
        if post_commit_results:
            self._results.extend(post_commit_results)
        # ``commit`` raises this the FIRST time it is called, then succeeds on
        # any later call. The persist commit is the only commit on the
        # in_progress/unexpired paths these tests drive, so the first commit IS
        # the persist commit. (The lazy-expire commit is on a path that 409s
        # before the persist, so it never collides with this injection.)
        self._commit_error = commit_error
        self._commit_calls = 0
        self.added: list = []
        self.committed = False
        self.refreshed: list = []
        self.rolled_back = False

    async def execute(self, *args, **kwargs):
        if not self._results:  # pragma: no cover - defensive
            raise AssertionError("unexpected extra db.execute call")
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self._commit_calls += 1
        if self._commit_error is not None and self._commit_calls == 1:
            raise self._commit_error
        self.committed = True

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def rollback(self):
        self.rolled_back = True


def _make_quiz_session(
    *,
    id="sess-1",
    user_id=42,
    status="in_progress",
    current_index=0,
    question_ids=("q-alpha", "q-beta"),
    expires_in=timedelta(minutes=10),
):
    """Build a real ``QuizSession`` ORM instance in memory (no DB).

    ``expires_at`` is tz-aware UTC offset by ``expires_in`` (negative -> already
    expired). The object is plain Python until flushed, which is all the route
    needs since the fake session never flushes.
    """
    from datetime import UTC, datetime

    qs = QuizSession(
        session_token_hash="x" * 64,
        test_id=1,
        submission_id=None,
        user_id=user_id,
        question_ids=list(question_ids),
        server_now=datetime.now(UTC),
        expires_at=datetime.now(UTC) + expires_in,
        status=status,
        current_index=current_index,
    )
    qs.id = id
    return qs


def _make_prior_answer(
    *, question_id="q-alpha", score=0.5, is_correct=False, idempotency_key="key-1"
):
    """A previously-persisted ``Answer`` row for the idempotency-replay path."""
    a = Answer(
        session_id="sess-1",
        question_id=question_id,
        submitted_answers=["a"],
        score=score,
        is_correct=is_correct,
        idempotency_key=idempotency_key,
    )
    a.id = "ans-prior"
    return a


def _override_answer_db(session: _AnswerSession):
    async def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db


def _patch_fetch_correct_answers(monkeypatch, *, qtype, correct_answers):
    """Patch the server-side answer-key fetch so no network is made.

    Returns a counter object exposing ``.calls`` so a test can assert the fetch
    was (or was NOT) invoked — the idempotency-replay test relies on this to
    prove the scoring path is skipped on a replay.
    """

    class _Counter:
        def __init__(self):
            self.calls = 0

    counter = _Counter()

    async def _fake_fetch(question_id, correlation_id):
        counter.calls += 1
        return qtype, correct_answers

    monkeypatch.setattr(_answer_route_mod, "_fetch_correct_answers", _fake_fetch)
    return counter


# ---------------------------------------------------------------------------
# Happy path -> 200, score 1.0, cursor advances, still in_progress
# ---------------------------------------------------------------------------
def test_submit_answer_happy_path_correct(client, override_user, monkeypatch):
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["question_id"] == "q-alpha"
    assert body["score"] == 1.0
    assert body["is_correct"] is True
    # cursor advanced from 0 -> 1, NOT the last question (2 total) -> still open
    assert body["current_index"] == 1
    assert body["status"] == "in_progress"
    # the answer key was fetched server-side exactly once
    assert fetch.calls == 1
    # the answer row was persisted with the server-computed score
    assert session.added and session.added[0].score == 1.0
    assert session.added[0].is_correct is True


# ---------------------------------------------------------------------------
# Multi-select partial credit flows through to the response
# ---------------------------------------------------------------------------
def test_submit_answer_multi_partial_credit(client, override_user, monkeypatch):
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    # correct {1,2,3}; submit {1,2} -> Jaccard 2/3
    _patch_fetch_correct_answers(monkeypatch, qtype="multi", correct_answers=[1, 2, 3])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [1, 2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] == pytest.approx(2 / 3)
    assert body["is_correct"] is False
    assert body["current_index"] == 1
    assert body["status"] == "in_progress"


# ---------------------------------------------------------------------------
# Wrong answer -> 200 with score 0.0 (the answer is still recorded)
# ---------------------------------------------------------------------------
def test_submit_answer_wrong_is_recorded_with_zero_score(
    client, override_user, monkeypatch
):
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [1]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score"] == 0.0
    assert body["is_correct"] is False
    # a wrong answer is still durably recorded
    assert session.added and session.added[0].is_correct is False


# ---------------------------------------------------------------------------
# Last-question path -> answering the final question flips status to submitted
# ---------------------------------------------------------------------------
def test_submit_answer_last_question_flips_to_submitted(
    client, override_user, monkeypatch
):
    # current_index already at the last slot (1 of a 2-question list); answering
    # advances to 2 == len -> status flips to submitted.
    qs = _make_quiz_session(current_index=1, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-beta", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_index"] == 2
    assert body["status"] == "submitted"


# ---------------------------------------------------------------------------
# Server-authoritative key: correct answers are fetched server-side and the
# response NEVER leaks a correct-answer field.
# ---------------------------------------------------------------------------
def test_submit_answer_does_not_leak_correct_answer_key(
    client, override_user, monkeypatch
):
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(
        monkeypatch, qtype="mcq", correct_answers=[2]
    )

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            # the client does NOT send a key, and even if it did it is ignored;
            # the server fetches the key itself.
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # the key came from the server-side fetch, not the request body
    assert fetch.calls == 1
    # the response carries ONLY the candidate-safe outcome shape
    assert set(body) == {
        "question_id",
        "score",
        "is_correct",
        "current_index",
        "status",
    }
    assert "correct_answers" not in body
    assert "correct_answer" not in body
    assert "sample_answer" not in body


# ---------------------------------------------------------------------------
# Idempotency replay -> returns the prior result WITHOUT re-scoring
# (returns before the scoring step, so this is a HARD assertion, not xfail)
# ---------------------------------------------------------------------------
def test_submit_answer_idempotency_replay_returns_prior_without_rescoring(
    client, override_user, monkeypatch
):
    qs = _make_quiz_session(current_index=1, question_ids=("q-alpha", "q-beta"))
    prior = _make_prior_answer(
        question_id="q-alpha", score=0.5, is_correct=False, idempotency_key="key-1"
    )
    session = _AnswerSession(
        quiz_session=qs, prior_answer=prior, with_idempotency=True
    )
    _override_answer_db(session)
    # patch the fetch so we can prove it is NEVER called on a replay
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
            headers={"Idempotency-Key": "key-1"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # the PRIOR row's outcome is echoed verbatim, scored exactly once
    assert body["question_id"] == "q-alpha"
    assert body["score"] == 0.5
    assert body["is_correct"] is False
    # the cursor/status are read from the (unmutated) session
    assert body["current_index"] == 1
    # the scoring path was NOT re-entered: no key fetch, no new answer persisted
    assert fetch.calls == 0
    assert session.added == []
    assert session.committed is False


# ---------------------------------------------------------------------------
# 409 when the session is already submitted (returns before scoring)
# ---------------------------------------------------------------------------
def test_submit_answer_409_when_session_submitted(client, override_user, monkeypatch):
    qs = _make_quiz_session(status="submitted")
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409
    assert "submitted" in resp.json()["detail"].lower()
    # the gate short-circuits before any scoring / persist
    assert fetch.calls == 0
    assert session.added == []


# ---------------------------------------------------------------------------
# 409 when the session has expired by the wall clock (lazy expire -> 409)
# ---------------------------------------------------------------------------
def test_submit_answer_409_when_session_expired(client, override_user, monkeypatch):
    # in_progress but expires_at is in the past -> the route lazily flips it to
    # 'expired', commits that, then refuses with 409.
    qs = _make_quiz_session(status="in_progress", expires_in=timedelta(minutes=-5))
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409
    assert "expired" in resp.json()["detail"].lower()
    # the session was flipped to expired and that flip was committed
    assert qs.status == "expired"
    assert session.committed is True
    # no scoring / answer persist happened
    assert fetch.calls == 0
    assert session.added == []


# ---------------------------------------------------------------------------
# 403 when the session belongs to a different candidate (returns before scoring)
# ---------------------------------------------------------------------------
def test_submit_answer_403_when_not_owner(client, override_user, monkeypatch):
    qs = _make_quiz_session(user_id=999)  # owned by someone else; FAKE_USER is 42
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 403
    assert "belong" in resp.json()["detail"].lower()
    assert fetch.calls == 0


# ---------------------------------------------------------------------------
# 404 when the session does not exist (returns before scoring)
# ---------------------------------------------------------------------------
def test_submit_answer_404_when_session_missing(client, override_user, monkeypatch):
    session = _AnswerSession(quiz_session=None)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/does-not-exist/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
    assert fetch.calls == 0


# ---------------------------------------------------------------------------
# 401 when identity headers are missing (real dependency, not overridden)
# ---------------------------------------------------------------------------
def test_submit_answer_missing_identity_401(client, monkeypatch):
    # Do NOT override get_current_user_from_headers: the real dependency 401s
    # before the route body runs (no DB override needed).
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    resp = client.post(
        "/v1/api/test-sessions/sess-1/answer",
        json={"question_id": "q-alpha", "submitted_answers": [2]},
    )

    assert resp.status_code == 401
    assert "authentication" in resp.json()["detail"].lower()
    assert fetch.calls == 0


# ---------------------------------------------------------------------------
# 401 when the resolved identity carries no id (defense-in-depth)
# ---------------------------------------------------------------------------
def test_submit_answer_identity_without_id_401(client, monkeypatch):
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    async def _user_no_id():
        return {"email": "x@example.com", "role": "PARTICIPANT"}

    app.dependency_overrides[get_current_user_from_headers] = _user_no_id
    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_current_user_from_headers, None)

    assert resp.status_code == 401
    assert "user id" in resp.json()["detail"].lower()
    assert fetch.calls == 0


# ===========================================================================
# Persist-race backstop: IntegrityError / generic SQLAlchemyError on the
# answer-persist commit (W3-F2 reviewer-flagged gaps)
# ===========================================================================
from sqlalchemy.exc import IntegrityError  # noqa: E402


def _integrity_error(msg: str = "duplicate key value violates unique constraint"):
    """A realistic ``IntegrityError`` carrying leaky SQL/value detail in ``orig``.

    The route maps this to either the winner's prior result (200) or a 409 — and
    must NEVER echo this text. Built with the (statement, params, orig) shape
    SQLAlchemy raises, so ``str(e)`` is non-empty and leak-prone.
    """
    return IntegrityError(
        "INSERT INTO answers ...",
        {"idempotency_key": "key-1", "leaky": "secret-value"},
        Exception(msg),
    )


# ---------------------------------------------------------------------------
# IntegrityError -> a concurrent writer already wrote the row (the "winner")
# -> 200 echoing the winner's result, no re-score, no 500.
# ---------------------------------------------------------------------------
def test_submit_answer_integrity_error_winner_exists_returns_prior_200(
    client, override_user, monkeypatch
):
    """Double-submit race backstop. Our persist ``commit`` loses to a concurrent
    writer (unique constraint -> ``IntegrityError``); ``_existing_answer`` then
    finds the winning row. The route rolls back and returns the WINNER's
    score/is_correct with a 200 — it does NOT re-score and does NOT 500.

    Drives ``_existing_answer``'s idempotency-key branch (an Idempotency-Key is
    sent, so the winner is found via the key lookup) plus the ``fresh``
    QuizSession re-read for the post-recovery cursor/status.
    """
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    winner = _make_prior_answer(
        question_id="q-alpha", score=1.0, is_correct=True, idempotency_key="key-1"
    )
    # The fresh re-read returns the session with the winner's already-advanced
    # cursor/status (a distinct instance from ``qs`` to prove the route reads the
    # re-fetched row, not the locally-mutated one).
    fresh = _make_quiz_session(
        current_index=1, question_ids=("q-alpha", "q-beta"), status="in_progress"
    )
    session = _AnswerSession(
        quiz_session=qs,
        # The initial idempotency-replay lookup MISSES (prior_answer=None): no
        # row existed when we checked, so we proceed to score+persist. The
        # concurrent winner is inserted between our lookup and our commit, which
        # is exactly what makes the commit hit the unique constraint.
        with_idempotency=True,
        prior_answer=None,
        commit_error=_integrity_error(),
        # post-commit: (1) _existing_answer key lookup -> winner,
        #              (2) fresh QuizSession re-read.
        post_commit_results=[
            _AnswerScalarResult(winner),
            _AnswerScalarResult(fresh),
        ],
    )
    _override_answer_db(session)
    # We DID reach scoring (the persist is downstream of the score call); the
    # fetch fires exactly once. The point is the WINNER's result is returned, not
    # this freshly-computed one.
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[1])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [1]},
            headers={"Idempotency-Key": "key-1"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # the WINNER's persisted outcome is echoed, NOT a re-score
    assert body["question_id"] == "q-alpha"
    assert body["score"] == 1.0
    assert body["is_correct"] is True
    # cursor/status come from the fresh re-read of the winning transaction
    assert body["current_index"] == 1
    assert body["status"] == "in_progress"
    # the losing transaction was rolled back; no 500 leaked
    assert session.rolled_back is True
    # scoring ran once (it is upstream of persist) but its result was discarded
    assert fetch.calls == 1
    # the leaky IntegrityError text never reaches the client
    assert "secret-value" not in resp.text
    assert "INSERT" not in resp.text


# ---------------------------------------------------------------------------
# IntegrityError -> no winner row found -> 409 (not 500).
# ---------------------------------------------------------------------------
def test_submit_answer_integrity_error_no_winner_returns_409(
    client, override_user, monkeypatch
):
    """Same persist ``IntegrityError`` but ``_existing_answer`` finds NO winning
    row (key lookup misses, per-question lookup misses). Per the route this is a
    409 ("Answer already recorded for this question") — never a 500, never an
    echo of the upstream error.

    With an Idempotency-Key set, ``_existing_answer`` issues TWO lookups (key,
    then per-question), both returning None.
    """
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(
        quiz_session=qs,
        # initial idempotency-replay lookup misses -> proceed to persist.
        with_idempotency=True,
        prior_answer=None,
        commit_error=_integrity_error(),
        # post-commit: key lookup -> None, then per-question lookup -> None.
        post_commit_results=[
            _AnswerScalarResult(None),
            _AnswerScalarResult(None),
        ],
    )
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[1])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [1]},
            headers={"Idempotency-Key": "key-1"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert "already recorded" in detail.lower()
    assert session.rolled_back is True
    assert fetch.calls == 1
    # no leak of the IntegrityError detail
    assert "secret-value" not in resp.text
    assert "INSERT" not in resp.text


# ---------------------------------------------------------------------------
# Generic SQLAlchemyError on persist (NOT an IntegrityError) -> clean 500,
# rollback awaited, no internal leak (mirrors create-session clean-500 test).
# ---------------------------------------------------------------------------
def test_submit_answer_db_error_is_clean_500(client, override_user, monkeypatch):
    """A non-integrity ``SQLAlchemyError`` on the persist commit is NOT a race;
    the route rolls back and returns a generic 500 ("Failed to record answer")
    without leaking ``str(e)``. No winner lookup is attempted (that branch is
    IntegrityError-only)."""
    boom = SQLAlchemyError("UPDATE quiz_sessions ... 'leaky-answer-value'")
    qs = _make_quiz_session(current_index=0, question_ids=("q-alpha", "q-beta"))
    session = _AnswerSession(quiz_session=qs, commit_error=boom)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 500, resp.text
    detail = resp.json()["detail"]
    assert detail == "Failed to record answer"
    # the raw SQL / leaky value must never reach the client
    assert "leaky-answer-value" not in detail
    assert "UPDATE" not in detail
    # the transaction was rolled back before raising
    assert session.rolled_back is True
    # scoring ran (upstream of persist), but the answer was never durably stored
    assert fetch.calls == 1


# ---------------------------------------------------------------------------
# Lazy-expire with a tz-NAIVE expires_at (the realistic SQLite read shape):
# an expired session whose stored expires_at has no tzinfo still flips to
# expired and 409s -> exercises the ``replace(tzinfo=UTC)`` branch (line 434).
# ---------------------------------------------------------------------------
def test_submit_answer_naive_expires_at_still_expires_409(
    client, override_user, monkeypatch
):
    """SQLite reads a ``DateTime`` column back as a tz-NAIVE ``datetime``. The
    route normalizes a naive ``expires_at`` to UTC before comparing it to a
    tz-aware ``now`` — without that branch the comparison would raise. A naive
    timestamp in the past must still lazily flip the session to ``expired`` and
    return 409."""
    from datetime import UTC, datetime, timedelta as _td

    qs = _make_quiz_session(status="in_progress")
    # Overwrite with a NAIVE past timestamp (no tzinfo), as SQLite would yield
    # a DateTime column read-back. Build it tz-aware then drop tzinfo so it is
    # genuinely naive without using the deprecated utcnow().
    qs.expires_at = (datetime.now(UTC) - _td(minutes=5)).replace(tzinfo=None)
    assert qs.expires_at.tzinfo is None  # precondition: genuinely naive
    session = _AnswerSession(quiz_session=qs)
    _override_answer_db(session)
    fetch = _patch_fetch_correct_answers(monkeypatch, qtype="mcq", correct_answers=[2])

    try:
        resp = client.post(
            "/v1/api/test-sessions/sess-1/answer",
            json={"question_id": "q-alpha", "submitted_answers": [2]},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409, resp.text
    assert "expired" in resp.json()["detail"].lower()
    # the naive comparison succeeded and the session flipped + committed
    assert qs.status == "expired"
    assert session.committed is True
    # no scoring / persist happened past the gate
    assert fetch.calls == 0
    assert session.added == []


# ===========================================================================
# _fetch_correct_answers error envelope — unit-test the helper DIRECTLY
# (the answer-key fetch never echoes the upstream body into the raised detail)
# ===========================================================================
import asyncio  # noqa: E402

from fastapi import HTTPException  # noqa: E402


def _call_fetch(monkeypatch, *, response=None, raises=None):
    """Patch the qms client and invoke ``_fetch_correct_answers`` directly.

    Mirrors ``_patch_qms`` but for the single-question GET. Returns the helper's
    return value (the ``(qtype, correct_answers)`` tuple) or raises the route's
    ``HTTPException``. ``UPSTREAM_LEAK`` is a sentinel embedded in every error
    body/exception so each test can assert it is never surfaced to the caller.
    """
    fake = _FakeQmsClient(response=response, raises=raises)
    monkeypatch.setattr(http_client, "get_qms_client", lambda: fake)
    monkeypatch.setattr(_answer_route_mod, "get_qms_client", lambda: fake)
    return asyncio.run(
        _answer_route_mod._fetch_correct_answers("q-alpha", "corr-1")
    )


UPSTREAM_LEAK = "UPSTREAM-LEAK-do-not-echo"


def test_fetch_correct_answers_happy_path_returns_type_and_key(monkeypatch):
    """The helper unwraps qms' ``type``/``correct_answers`` from a 200 body."""
    qtype, key = _call_fetch(
        monkeypatch,
        response=_FakeResponse(
            200, {"type": "mcq", "correct_answers": [2], "question_text": "x"}
        ),
    )
    assert qtype == "mcq"
    assert key == [2]


def test_fetch_correct_answers_404_maps_to_404(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _call_fetch(
            monkeypatch,
            response=_FakeResponse(404, {"detail": UPSTREAM_LEAK}),
        )
    assert ei.value.status_code == 404
    assert ei.value.detail == "Question not found"
    assert UPSTREAM_LEAK not in str(ei.value.detail)


def test_fetch_correct_answers_5xx_maps_to_502(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _call_fetch(
            monkeypatch,
            response=_FakeResponse(503, {"detail": UPSTREAM_LEAK}),
        )
    assert ei.value.status_code == 502
    assert ei.value.detail == "Question service is unavailable"
    assert UPSTREAM_LEAK not in str(ei.value.detail)


def test_fetch_correct_answers_4xx_maps_to_500_contract(monkeypatch):
    # a non-404 4xx (e.g. 400/422) is a contract error -> generic 500.
    with pytest.raises(HTTPException) as ei:
        _call_fetch(
            monkeypatch,
            response=_FakeResponse(422, {"detail": UPSTREAM_LEAK}),
        )
    assert ei.value.status_code == 500
    assert "contract" in str(ei.value.detail).lower()
    assert UPSTREAM_LEAK not in str(ei.value.detail)


def test_fetch_correct_answers_non_json_body_maps_to_500_contract(monkeypatch):
    # 200 OK but .json() raises -> upstream contract drift -> generic 500.
    with pytest.raises(HTTPException) as ei:
        _call_fetch(
            monkeypatch,
            response=_FakeResponse(200, ValueError(UPSTREAM_LEAK)),
        )
    assert ei.value.status_code == 500
    assert "contract" in str(ei.value.detail).lower()
    assert UPSTREAM_LEAK not in str(ei.value.detail)


def test_fetch_correct_answers_transport_error_maps_to_502(monkeypatch):
    # httpx.RequestError (DNS/connect/timeout) -> 502, upstream text not echoed.
    with pytest.raises(HTTPException) as ei:
        _call_fetch(
            monkeypatch,
            raises=httpx.ConnectError(UPSTREAM_LEAK),
        )
    assert ei.value.status_code == 502
    assert ei.value.detail == "Question service is unavailable"
    assert UPSTREAM_LEAK not in str(ei.value.detail)
