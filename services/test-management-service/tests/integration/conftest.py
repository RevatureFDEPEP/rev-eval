"""Fixtures for the integration suite (W3-F5) — real databases, no mocks.

Prerequisite containers (from the repo root):

    docker compose up -d --wait postgres mongo question-management-service

What "real" means here:

* **Postgres** — a dedicated ``eval_ai_itest`` database is dropped/recreated
  once per pytest session and migrated with ``alembic upgrade head``, so the
  suite exercises the exact schema production runs (including the
  ``SELECT FOR UPDATE`` row-lock semantics SQLite cannot emulate).
* **Mongo + question-management-service** — session creation calls the *real*
  service over HTTP, which runs the real ``$sample`` aggregation against the
  real Mongo container. The question bank is seeded directly via pymongo.

Connection knobs (defaults match the published docker-compose ports):

    IT_POSTGRES_ADMIN_URL   postgresql://root:root@localhost:5432/postgres
    IT_DATABASE_URL         postgresql+asyncpg://root:root@localhost:5432/eval_ai_itest
    IT_MONGO_URI            mongodb://admin:admin@localhost:27017/?authSource=admin
    IT_MONGO_DB             evalai
    IT_QUESTION_SERVICE_URL http://localhost:8003

Note on wiring: ``src.config.settings.Settings()`` is instantiated while
pytest loads ``tests/conftest.py`` (it imports the models), i.e. *before* any
pytest hook could export env vars — so the integration targets are applied at
fixture time instead: ``app_client`` rebinds ``settings.QUESTION_SERVICE_URL``
and rebuilds the question-client singleton, ``get_db`` is overridden onto the
integration engine, and the Alembic subprocess gets DATABASE_URL explicitly.
The module-global engine in ``src.db.session`` is never connected here
(startup ``init_db()`` doesn't run under ASGITransport).
"""
import asyncio
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from fastapi import Header
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
IT_MONGO_DB = os.getenv("IT_MONGO_DB", "evalai")
IT_QUESTION_SERVICE_URL = os.getenv(
    "IT_QUESTION_SERVICE_URL", "http://localhost:8003"
)

_HINT = (
    "start the containers first: "
    "`docker compose up -d --wait postgres mongo question-management-service` "
    "(from the repo root)"
)


def _asyncpg_url(url: str) -> str:
    """asyncpg.connect wants a plain postgresql:// DSN, not the SQLAlchemy form."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


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

    conn = await asyncpg.connect(_asyncpg_url(IT_DATABASE_URL), timeout=10)
    try:
        # Stub of the user-service-owned ``users`` table. Alembic revision 0003
        # seeds demo data by looking up TRAINER/PARTICIPANT ids; in the shared
        # dev database compose ordering guarantees user-service has created and
        # seeded ``users`` before this service migrates. The integration DB is
        # isolated, so that precondition is recreated minimally here.
        await conn.execute(
            "CREATE TABLE users ("
            "id SERIAL PRIMARY KEY, email VARCHAR(255), role VARCHAR(50))"
        )
        await conn.execute(
            "INSERT INTO users (email, role) VALUES "
            "('it-trainer@example.com', 'TRAINER'), "
            "('it-participant-1@example.com', 'PARTICIPANT'), "
            "('it-participant-2@example.com', 'PARTICIPANT')"
        )
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def pg_database() -> str:
    """Fresh ``eval_ai_itest`` database, migrated to the Alembic head.

    Synchronous on purpose: pytest-asyncio (auto mode) gives each test a
    function-scoped event loop, so session-scoped provisioning runs in its own
    short-lived loop via ``asyncio.run`` and the migration runs in a
    subprocess (Alembic's async env.py calls ``asyncio.run`` itself and cannot
    be invoked from inside a running loop).
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
    """Fail fast with a actionable message if the real service isn't up."""
    try:
        resp = httpx.get(f"{IT_QUESTION_SERVICE_URL}/health", timeout=5)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"question-management-service unreachable at "
            f"{IT_QUESTION_SERVICE_URL} ({e}) — {_HINT}"
        )
    return IT_QUESTION_SERVICE_URL


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
      and nothing touches the module-global engine's pool).
    * ``get_current_user_from_headers`` → the production dependency resolves
      the user by calling user-service over HTTP; that hop is out of scope for
      this suite (sessions/locking/scoring vs real DBs), so the override keeps
      the gateway's header-driven contract without the network call.
    """
    from main import app
    from src.config.settings import settings
    from src.db.session import get_db
    from src.utils import question_client
    from src.utils.dependencies import get_current_user_from_headers

    # Settings was instantiated before any hook could set env (see module
    # docstring): point it at the host-published service port and rebuild the
    # singleton client so it binds the new base_url.
    original_question_url = settings.QUESTION_SERVICE_URL
    settings.QUESTION_SERVICE_URL = IT_QUESTION_SERVICE_URL
    await question_client.aclose()

    async def _get_db():
        async with it_db() as session:
            yield session

    async def _user_from_headers(
        x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
        x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
        x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    ) -> Dict[str, Any]:
        return {
            "id": int(x_user_id or 1),
            "email": x_user_email or "it-participant-1@example.com",
            "role": x_user_role or "PARTICIPANT",
        }

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user_from_headers] = _user_from_headers
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://integration",
            headers={"X-User-Id": "2", "X-User-Role": "PARTICIPANT"},
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        settings.QUESTION_SERVICE_URL = original_question_url
        await question_client.aclose()


@pytest.fixture
def mongo_questions(question_service):
    """Seed tagged question documents straight into the real Mongo container.

    Returns a ``seed(n, qtype)`` callable; every inserted document is removed
    on teardown so the shared ``evalai`` database stays clean. ``$sample`` may
    still return pre-existing dev documents — tests must assert on session
    invariants, never on *which* questions were sampled.
    """
    try:
        client = MongoClient(IT_MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Mongo unreachable at {IT_MONGO_URI} ({e}) — {_HINT}")

    collection = client[IT_MONGO_DB]["questions"]
    tag = f"it-{uuid4().hex[:10]}"
    inserted_ids = []

    def seed(n: int = 3, qtype: str = "mcq"):
        now = datetime.now(timezone.utc)
        docs = [
            {
                "type": qtype,
                "question_text": f"Integration question {i} [{tag}] — pick option two.",
                "options": [
                    {"option_id": j, "text": f"Option {j} of question {i}"}
                    for j in range(1, 5)
                ],
                "correct_answers": [2],
                "answer_explanation": "Seeded by the W3-F5 integration suite.",
                "difficulty": "easy",
                "skills": [],
                "tags": [tag],
                "created_at": now,
                "updated_at": now,
            }
            for i in range(n)
        ]
        result = collection.insert_many(docs)
        inserted_ids.extend(result.inserted_ids)
        return [str(_id) for _id in result.inserted_ids]

    yield seed

    if inserted_ids:
        collection.delete_many({"_id": {"$in": inserted_ids}})
    client.close()


@pytest_asyncio.fixture
async def make_test(it_db):
    """Insert a ``tests`` row to start sessions against.

    No teardown: the whole database is dropped and recreated next session, and
    sessions/answers reference the row via FKs within the run.
    """
    from src.models.test import Test, TestType

    async def _make(
        number_of_questions: int = 3,
        duration: timedelta = timedelta(minutes=30),
    ):
        async with it_db() as session:
            test = Test(
                name=f"IT quiz {uuid4().hex[:8]}",
                test_type=TestType.QUIZ,
                duration=duration,
                number_of_questions=number_of_questions,
                created_by_id=1,
                active=True,
            )
            session.add(test)
            await session.commit()
            await session.refresh(test)
            return test

    return _make
