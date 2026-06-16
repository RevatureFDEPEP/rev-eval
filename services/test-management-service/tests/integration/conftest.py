"""Fixtures for the W3-F5 integration suite — real databases, no mocks.

Prerequisite containers (from the repo root):

    docker compose up -d --wait postgres mongo question-management-service

What "real" means here:

* **Postgres** — a dedicated ``eval_ai_itest`` database is dropped/recreated
  once per pytest session and migrated with ``alembic upgrade head`` (the real
  0001→0007 chain), so the suite exercises the exact schema production runs —
  including the ``SELECT FOR UPDATE`` row-lock semantics SQLite cannot emulate.
* **Mongo + question-management-service** — session creation calls the *real*
  service over HTTP, which runs the real ``$sample`` aggregation (``{$match:
  {skills: {$in: [...]}}}``) against the real Mongo container. The question
  bank is seeded directly via pymongo under a unique per-test skill tag.

Connection knobs (defaults match the published docker-compose host ports):

    IT_POSTGRES_ADMIN_URL   postgresql://root:root@localhost:5432/postgres
    IT_DATABASE_URL         postgresql+asyncpg://root:root@localhost:5432/eval_ai_itest
    IT_MONGO_URI            mongodb://admin:admin@localhost:27017/?authSource=admin
    IT_MONGO_DB             evalai
    IT_QUESTION_SERVICE_URL http://localhost:8003

Wiring note: ``src.config.settings.Settings()`` is built while pytest loads
``tests/conftest.py`` (it imports the models), i.e. before any hook could
export env vars — so the integration targets are applied at fixture time:
``app_client`` rebinds ``settings.QUESTION_MANAGEMENT_SERVICE_URL`` (the
session service builds the QMS URL per-call from settings, so the singleton
client needs no rebuild) and overrides ``get_db`` onto the integration engine,
and the Alembic subprocess gets ``DATABASE_URL`` explicitly. The module-global
engine in ``src.db.session`` is never connected (startup ``init_db()`` does not
run under ASGITransport).
"""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from pymongo import MongoClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

SERVICE_ROOT = Path(__file__).resolve().parents[2]

IT_ADMIN_URL = os.getenv(
    "IT_POSTGRES_ADMIN_URL", "postgresql://root:root@localhost:5432/postgres"
)
IT_DB_NAME = "eval_ai_itest"
IT_DATABASE_URL = os.getenv(
    "IT_DATABASE_URL",
    f"postgresql+asyncpg://root:root@localhost:5432/{IT_DB_NAME}",
)
IT_MONGO_URI = os.getenv(
    "IT_MONGO_URI", "mongodb://admin:admin@localhost:27017/?authSource=admin"
)
# Must match the database question-management-service reads from: the
# cross-service $sample uses QMS's own connection, so an isolated DB name here
# would make seeded questions invisible to it. Default off the SAME MONGO_DB env
# var the QMS container is configured with (compose: `MONGO_DB: ${MONGO_DB:-evalai}`)
# so the two can't silently drift apart; IT_MONGO_DB still overrides for unusual
# setups. The seed fixture also preflights QMS to catch any residual mismatch loudly.
IT_MONGO_DB = os.getenv("IT_MONGO_DB") or os.getenv("MONGO_DB", "evalai")
IT_QUESTION_SERVICE_URL = os.getenv("IT_QUESTION_SERVICE_URL", "http://localhost:8003")

# Stable tag on every seeded question doc so a session-scoped sweep can remove
# this suite's docs — including orphans left in the shared collection by a
# previous run that crashed before its per-test teardown deleted them.
IT_DOC_MARKER = "w3f5-it"

_HINT = (
    "start the containers first: "
    "`docker compose up -d --wait postgres mongo question-management-service` "
    "(from the repo root)"
)


async def _provision_database() -> None:
    try:
        admin = await asyncpg.connect(IT_ADMIN_URL, timeout=10)
    except Exception as e:  # noqa: BLE001 — any connect failure means "not up"
        pytest.fail(f"Postgres unreachable at {IT_ADMIN_URL} ({e}) — {_HINT}")
    try:
        # WITH (FORCE): kill stragglers from an interrupted previous run.
        await admin.execute(f'DROP DATABASE IF EXISTS "{IT_DB_NAME}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{IT_DB_NAME}"')
    finally:
        await admin.close()


@pytest.fixture(scope="session")
def pg_database() -> str:
    """Fresh ``eval_ai_itest`` database, migrated to the Alembic head.

    Synchronous on purpose: pytest-asyncio gives each test a function-scoped
    event loop, so session-scoped provisioning runs in its own short-lived loop
    via ``asyncio.run`` and the migration runs in a subprocess (Alembic's async
    env.py calls ``asyncio.run`` itself and cannot be nested in a running loop).
    """
    asyncio.run(_provision_database())

    env = {**os.environ, "DATABASE_URL": IT_DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=SERVICE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(
            "alembic upgrade head failed against the integration DB:\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return IT_DATABASE_URL


@pytest.fixture(scope="session")
def question_service() -> str:
    """Fail fast with an actionable message if the real service isn't up."""
    try:
        resp = httpx.get(f"{IT_QUESTION_SERVICE_URL}/health", timeout=5)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"question-management-service unreachable at "
            f"{IT_QUESTION_SERVICE_URL} ({e}) — {_HINT}"
        )
    return IT_QUESTION_SERVICE_URL


@pytest.fixture(scope="session", autouse=True)
def _mongo_orphan_sweep():
    """Sweep this suite's question docs from the shared collection at session
    start and end, so a previous run that died before its per-test teardown
    can't leave orphan ``w3f5-it`` docs accumulating in the dev Mongo."""
    try:
        client = MongoClient(IT_MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception:  # noqa: BLE001 — Mongo down is reported by the seed fixture
        yield
        return
    collection = client[IT_MONGO_DB]["questions"]
    collection.delete_many({"tags": IT_DOC_MARKER})
    yield
    collection.delete_many({"tags": IT_DOC_MARKER})
    client.close()


@pytest_asyncio.fixture
async def it_db(pg_database):
    """Session factory on the integration DB for seeding and row assertions.

    Function-scoped with ``NullPool`` so every connection lives entirely inside
    the current test's event loop (asyncpg connections cannot hop loops).
    """
    engine = create_async_engine(IT_DATABASE_URL, poolclass=NullPool)
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(pg_database, question_service, it_db):
    """The real FastAPI app over ASGI, talking to the real integration DB.

    Two dependency overrides, both deliberate:

    * ``get_db`` → sessions minted from ``it_db`` so each request gets its own
      asyncpg connection (real row-lock contention between concurrent requests,
      nothing touches the module-global engine's pool).
    * ``get_current_participant_id`` → the production dependency resolves the
      user by calling user-service over HTTP; that hop is out of scope for this
      suite (sessions/locking/scoring vs real DBs) and user-service is not in
      the integration container set, so the override honours the gateway's
      header-driven contract without the network call.
    """
    from fastapi import Header
    from main import app

    from src.config.settings import settings
    from src.db.session import get_db
    from src.utils.dependencies import get_current_participant_id
    from src.utils.question_client import close_question_client

    original_question_url = settings.QUESTION_MANAGEMENT_SERVICE_URL
    settings.QUESTION_MANAGEMENT_SERVICE_URL = IT_QUESTION_SERVICE_URL
    # The QMS httpx client is a module-global singleton bound to the event loop
    # it was first created on. pytest-asyncio gives each test a fresh loop, so
    # discard any client from a prior test — get_question_client() rebuilds it
    # lazily on this test's loop, avoiding "Event loop is closed".
    await close_question_client()

    async def _get_db():
        async with it_db() as session:
            yield session

    async def _participant_id(
        x_user_id: str | None = Header(None, alias="X-User-Id"),
    ) -> int:
        return int(x_user_id or 2)

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_participant_id] = _participant_id
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://integration",
            headers={"X-User-Id": "2", "X-User-Role": "PARTICIPANT"},
        ) as client:
            yield client
    finally:
        # Remove only the overrides this fixture installed, so a future fixture
        # that overrides something else on the shared app isn't clobbered.
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_participant_id, None)
        settings.QUESTION_MANAGEMENT_SERVICE_URL = original_question_url
        # Close the client on this (still-open) loop so the next test's
        # get_question_client() starts clean rather than inheriting a client
        # pinned to a loop that is about to close.
        await close_question_client()


@pytest_asyncio.fixture
async def seed_quiz(it_db, question_service):
    """Returns ``await seed(n, qtype, duration)`` → a startable quiz.

    Each call: (1) inserts ``n`` question docs straight into the real Mongo
    ``questions`` collection under a unique skill tag, then (2) creates the
    matching ``Skill`` + ``Test`` + ``TestSkill`` rows in Postgres so the
    skill-filtered ``$sample`` in session creation returns exactly this set.

    Returns a dict: ``{test_id, skill_name, mongo_ids, n}``. Mongo docs are
    deleted on teardown; the Postgres rows ride along with the per-session DB
    drop. ``$sample`` can only ever return *our* docs because the skill tag is
    a fresh UUID, so tests may assert on counts/ids deterministically.
    """
    from src.models.skill import Skill
    from src.models.test import Test, TestType
    from src.models.test_skill import TestSkill

    try:
        mongo = MongoClient(IT_MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo.admin.command("ping")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Mongo unreachable at {IT_MONGO_URI} ({e}) — {_HINT}")
    collection = mongo[IT_MONGO_DB]["questions"]
    inserted_ids: list = []

    async def seed(
        n: int = 3,
        qtype: str = "mcq",
        duration: timedelta = timedelta(minutes=30),
    ) -> dict:
        skill_name = f"it-skill-{uuid4().hex[:12]}"
        docs = [
            {
                "type": qtype,
                "question_text": (
                    f"Integration question {i} [{skill_name}] — the answer is option 2."
                ),
                "options": [
                    {"option_id": j, "text": f"Option {j} of question {i}"}
                    for j in range(1, 5)
                ],
                "correct_answers": [2],
                "answer_explanation": "Seeded by the W3-F5 integration suite.",
                "difficulty": "easy",
                "skills": [skill_name],
                "tags": [skill_name, IT_DOC_MARKER],
            }
            for i in range(n)
        ]
        result = collection.insert_many(docs)
        inserted_ids.extend(result.inserted_ids)
        mongo_ids = [str(_id) for _id in result.inserted_ids]

        async with it_db() as db:
            skill = Skill(name=skill_name, description="W3-F5 integration skill")
            db.add(skill)
            await db.flush()
            test = Test(
                name=f"IT quiz {uuid4().hex[:8]}",
                test_type=TestType.QUIZ,
                duration=duration,
                number_of_questions=n,
                created_by_id=1,
                active=True,
            )
            db.add(test)
            await db.flush()
            db.add(TestSkill(test_id=test.id, skill_id=skill.id))
            await db.commit()
            test_id = test.id

        # Loud preflight: confirm QMS actually sees what we just seeded. The docs
        # go into IT_MONGO_DB, but the cross-service $sample reads from QMS's own
        # MONGO_DB; if those drift, the docs are invisible and session creation
        # would later fail with a confusing "not enough questions" 409. Asserting
        # it here turns a silent DB-name mismatch into a clear, actionable failure.
        # The skill tag is a fresh UUID, so $sample can only ever return our n docs.
        async with httpx.AsyncClient(timeout=10) as client:
            probe = await client.get(
                f"{IT_QUESTION_SERVICE_URL}/v1/api/questions/sample",
                params=[("skills", skill_name), ("count", str(n))],
            )
        visible = probe.json() if probe.status_code == 200 else []
        if probe.status_code != 200 or len(visible) != n:
            pytest.fail(
                f"QMS saw {len(visible)}/{n} freshly-seeded questions for skill "
                f"'{skill_name}' (HTTP {probe.status_code}). The suite seeded into "
                f"Mongo DB '{IT_MONGO_DB}', but question-management-service reads "
                f"its own MONGO_DB — if those differ the seeded docs are invisible "
                f"to $sample. Align IT_MONGO_DB / MONGO_DB."
            )

        return {
            "test_id": test_id,
            "skill_name": skill_name,
            "mongo_ids": mongo_ids,
            "n": n,
        }

    yield seed

    if inserted_ids:
        collection.delete_many({"_id": {"$in": inserted_ids}})
    mongo.close()


@pytest_asyncio.fixture
async def start_session(app_client, seed_quiz):
    """Returns ``await start(n)`` → ``(session_id, question_id)`` for a fresh,
    seeded ``n``-question quiz. Shared by the integration tests that need a
    started session without re-asserting the create-response contract."""

    async def start(n_questions: int) -> tuple[str, str]:
        quiz = await seed_quiz(n=n_questions, duration=timedelta(minutes=30))
        resp = await app_client.post(
            "/v1/api/sessions", json={"test_id": quiz["test_id"]}
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        session_id = str(uuid.UUID(body["session_id"]))
        return session_id, body["question"]["id"]

    return start
