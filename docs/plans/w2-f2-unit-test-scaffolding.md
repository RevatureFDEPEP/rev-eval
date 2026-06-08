# W2-F2 — Complete Unit Test Scaffolding (Frontend + Backend)

## Context

W2-F2 (`docs/features/w2-f2-unit-test-scaffolding.md`) is 🟡 In Progress. Steps 1 & 2
landed *shallow*: 1 frontend test file, and 1–3 smoke/mock test files per backend
service. Three things remain:

- **(A)** Frontend coverage breadth (currently 1 file).
- **(B)** Backend test *depth* — parameterized tests on models, repository CRUD, and
  Pydantic schemas, plus **dedicated test databases** for repo-level tests.
- **(C)** Multi-stage Dockerfile **test stages** so CI can run pytest inside the image.

This matters because W2-F2 **unblocks W3-F2** (scoring engine — needs pytest wired in
test-management-service) and **W3-F5** (integration tests build on this scaffolding).
W3-F5 owns *real* Postgres/Mongo integration, so the test DBs added here are
**hermetic in-memory** (aiosqlite + mongomock-motor) — fast, no external services.

Decisions locked with user: **scope = all three (A+B+C)**, **test DB = hermetic in-memory**.

---

## Git workflow

- Work in `rev-eval/` (the git repo; workspace root is not). Currently on `richardh` with
  **uncommitted working-tree changes** (FEATURE_STATUS.md modified + `docs/features/*` renamed
  `fN-*` → `wX-fY-*`). **Carry these onto the new branch**: `git checkout -b richardh-feat-W2-F2`
  from `richardh` brings the uncommitted changes along automatically — do NOT commit them to
  `richardh` first. They become part of the docs milestone commit on the feature branch.
- Branch name `richardh-feat-W2-F2` (matches `richardh-feat-*` convention seen on existing branches).
- **Commit per milestone** (one commit at each boundary below), normal-prose messages,
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`:
  1. `B1` — add `requirements-dev.txt` ×4 + CI dev-deps switch
  2. `B2`+`B3` — conftest fixtures + parameterized model/repo/schema tests (can split per service if large)
  3. `C` — multi-stage Dockerfile test stages ×4
  4. `A` — frontend vitest setup + new test files
  5. docs — W2-F2 detail file + FEATURE_STATUS row → ✅
- Do **not** push or open a PR unless the user asks.

---

## Current-state facts (from exploration)

- pytest / pytest-cov / ruff are **installed at CI time only** (`ci-pipeline.yml` line ~96),
  **not** checked into any `requirements.txt`. No `requirements-dev.txt` exists.
- No real pytest fixtures anywhere; async tests use `asyncio.run()` + `AsyncMock`, not pytest-asyncio.
- `services/*/conftest.py` are env-only bootstraps; `pytest.ini` per service (`pythonpath=.`, `testpaths=tests`).
- `test-management-service`: async SQLAlchemy (asyncpg), schema owned by **Alembic** (`init_db` = connectivity only). `session.py` already converts to async URL and **passes through `sqlite+aiosqlite://` untouched** (line 25).
- `user-service`: **sync** SQLAlchemy (psycopg2); `user_repository.py` is an **empty stub** — test the `User` model + `AuthService` + schemas instead.
- `question-management-service`: Beanie/Motor over Mongo; `QuestionRepository` is full async CRUD.
- `api-gateway-service`: **no DB/models/repos** — deepen routing + auth-boundary tests only.
- All 4 backend Dockerfiles are **single-stage** `python:3.11-slim`. Frontend Dockerfile is already 3-stage.

---

## Area B — Backend test depth + hermetic test DBs

### B1. Add `requirements-dev.txt` per backend service
Create `services/<svc>/requirements-dev.txt` (one line `-r requirements.txt` then dev deps).
This single change feeds **both** the Dockerfile test stage (C) and local dev, and removes
the CI-time `pip install pytest...` hack.

- All services: `pytest`, `pytest-cov`, `ruff`
- async-DB services (test-management, question-management): `pytest-asyncio`
- test-management & user-service: `aiosqlite` (async sqlite) — user-service also fine with sync `sqlite://`
- question-management: `mongomock-motor` (Beanie-compatible Motor mock)

Pin loosely (e.g. `pytest>=8,<9`). Update CI step to `pip install -r requirements-dev.txt`
instead of the inline `pip install pytest pytest-cov ruff` (`.github/workflows/ci-pipeline.yml`).

### B2. Real DB-session fixtures in `conftest.py`

**test-management-service** (`services/test-management-service/conftest.py`):
- Add `pytest_asyncio` fixture `db_session`: build a fresh `create_async_engine("sqlite+aiosqlite:///:memory:")`,
  `Base.metadata.create_all` (import all models so metadata is populated — mirror the
  import list in `session.py:init_db`), yield an `AsyncSession`, dispose after.
- **Do NOT reuse the module-global `engine`** (it's bound to env DATABASE_URL at import). Build a test-local engine in the fixture.
- Add `[tool.pytest.ini_options] asyncio_mode = "auto"` (or `pytest.ini` equivalent) so `async def test_*` run without per-test decorators.
- **Risk to verify during impl:** if any model (`test.py`, `test_submission.py`) uses Postgres-only column types (JSONB/ARRAY), `create_all` on SQLite fails. Check `src/models/*.py`; if found, either swap to SQLAlchemy-generic `JSON` or mark those repo tests `@pytest.mark.skipif` for sqlite and keep schema/mock coverage there.

**question-management-service** (`services/question-management-service/conftest.py`):
- Async fixture `beanie_db`: `mongomock_motor.AsyncMongoMockClient()` → `init_beanie(database=..., document_models=[Question])`. Yields nothing/the client; tests then use Beanie/`QuestionRepository` directly.

**user-service** (`services/user-service/conftest.py`):
- Sync fixture `db_session` over `sqlite://` (StaticPool, `connect_args={"check_same_thread": False}`), `Base.metadata.create_all`. Used only for `User` model persistence/uniqueness tests (repo is a stub).

### B3. Parameterized depth tests (new files, keep existing smoke files)

- **test-management-service** `tests/test_category_repository.py` (and optionally skill/test repos):
  real `CategoryRepository` CRUD against `db_session` — create→get_by_id→list→update→delete,
  `link_skill`/`unlink_skill` **idempotency** (the repo's documented edge cases), nested-skills eager load.
  Use `@pytest.mark.parametrize` for schema-validation matrices on `CategoryCreate/Update`, `SkillCreate/Update`.
- **question-management-service** `tests/test_question_repository.py`: `QuestionRepository` create/get/list(paginated)/update/delete/count + `find_by_type/skill/difficulty/tags` against `beanie_db`. Parametrize `QuestionCreate` type-aware validation (MCQ needs options+correct_answers; TEXT needs sample_answer).
- **user-service** `tests/test_user_model.py`: persist `User` via `db_session`, assert unique-email constraint, role enum, defaults. Extend existing `auth_schema` validation with parametrized cases.
- **api-gateway-service** `tests/test_routing.py`: parametrize the `ROUTES` regex table (pattern → service) and `X-User-*` header injection; assert public pass-throughs (`/v1/api/auth/login|register`) skip JWT and protected routes 401 without a token.

---

## Area C — Multi-stage Dockerfile test stages

Restructure each backend `services/<svc>/Dockerfile` into named stages (BuildKit; CI already builds images):

```dockerfile
FROM python:3.11-slim AS base
# WORKDIR, system deps (gcc/curl/postgresql-client), pip+setuptools+wheel+jaraco.context upgrade
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q          # fails the build if tests fail

FROM base AS production    # unchanged from today: copy code, non-root user, healthcheck, CMD
COPY . .
# ... existing useradd/chmod start.sh/EXPOSE/HEALTHCHECK/CMD ...
```

- Default target stays **production** (last stage), so `docker compose up --build` is unaffected.
- CI can add a `docker build --target test` step (optional) — note it in the plan but the
  primary CI test path remains the pip-install pytest job (now using `requirements-dev.txt`).
- Preserve every prod-image property already present per service: non-root `appuser` (api-gateway,
  test-management, question-management), healthchecks, `start.sh` CMD (test-management, question-management),
  the jaraco.context CVE upgrade line. user-service has no non-root user/healthcheck today — leave as-is.

Representative files: `services/api-gateway-service/Dockerfile`, `services/user-service/Dockerfile`,
`services/test-management-service/Dockerfile`, `services/question-management-service/Dockerfile`.

---

## Area A — Frontend test breadth

### A1. Test setup file
- Create `frontend/vitest.setup.ts` importing `@testing-library/jest-dom` (dep already present).
- Wire it in `frontend/vitest.config.ts` via `test.setupFiles: ["./vitest.setup.ts"]`.

### A2. New test files (vitest + @testing-library/react, jsdom already configured)
- **Zod schemas** `src/components/trainer/question-form-utils.test-extras` (or extend existing):
  `imageFileSchema` (png/jpg whitelist, 5MB cap), `trueFalseSchema`, `textSchema` edge cases — pure, high value.
- **Test-form schema**: `testFormSchema` in `src/app/(dashboard)/trainer/tests/create/page.tsx` — extract/import and parametrize valid/invalid.
- **Presentational quiz components** under `src/components/quiz/`: `QuestionCard.tsx` (type → MCQ/Multi/TrueFalse dispatch + difficulty badge), `MCQQuestion`/`MultiQuestion` selection logic, `Timer.tsx` (countdown formatting/expiry). Render + assert with testing-library.
- **Login layout** `src/app/_components/landing-auth.tsx`: login/register mode toggle, role select, error rendering (mock the BFF fetch).

---

## Critical files

| Purpose | Path |
|---|---|
| Backend dev deps (new ×4) | `services/<svc>/requirements-dev.txt` |
| Async sqlite fixture | `services/test-management-service/conftest.py` + `pytest.ini` |
| Beanie mock fixture | `services/question-management-service/conftest.py` |
| Sync sqlite fixture | `services/user-service/conftest.py` |
| New repo/model/routing tests | `services/<svc>/tests/test_*.py` |
| Dockerfile test stages ×4 | `services/<svc>/Dockerfile` |
| CI dev-deps install | `.github/workflows/ci-pipeline.yml` |
| Vitest setup | `frontend/vitest.setup.ts`, `frontend/vitest.config.ts` |
| Frontend tests | `frontend/src/components/quiz/*.test.tsx`, `frontend/src/app/_components/landing-auth.test.tsx` |
| Status updates | `docs/features/w2-f2-unit-test-scaffolding.md`, `docs/FEATURE_STATUS.md` |

Reuse existing helpers: `session.py` sqlite URL pass-through, `Base.metadata`, the documented
repo edge cases (link/unlink idempotency, eager `selectinload`), existing `conftest.py` env bootstrap.

---

## Verification

1. **Backend, per service** (`cd services/<svc>`):
   `pip install -r requirements-dev.txt && pytest -q --cov` — new model/repo/schema tests pass, coverage rises above existing `.coveragerc` baseline.
2. **Hermetic check**: run backend tests with Postgres/Mongo **down** — must still pass (proves in-memory DBs, no external deps).
3. **Dockerfile test stage**: `docker build --target test services/test-management-service` — pytest runs and the build fails if a test fails; `docker build` (default target) still produces a working prod image.
4. **Full stack unaffected**: `docker compose up --build` boots all services as before.
5. **Frontend** (`cd frontend`): `pnpm test` — new vitest files green; `pnpm build` still passes.
6. **CI dry-read**: confirm `ci-pipeline.yml` now installs `requirements-dev.txt` and pytest gate still runs only where `tests/` exists.
7. Update the W2-F2 detail file (check off steps 1–3 sub-items, add evidence) and the FEATURE_STATUS row to ✅ in the same change.
