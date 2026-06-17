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

    ``execute`` replays a scripted sequence of results (the route issues two
    queries: the Test lookup, then the skills join). ``add`` records the object;
    ``commit`` is a no-op (or raises, to drive the rollback path); ``refresh``
    populates the PK the way a real flush-then-refresh would; ``rollback``
    records that it was awaited.
    """

    def __init__(self, *, test, skill_rows, commit_error: Exception | None = None):
        # Result #1 = Test lookup; result #2 = skills join.
        self._results = [_ScalarResult(test), _RowsResult(skill_rows)]
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
    # session_token is 64 hex chars (secrets.token_hex(32) -> 256 bits)
    assert len(body["session_token"]) == 64
    int(body["session_token"], 16)  # raises if not hex

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
