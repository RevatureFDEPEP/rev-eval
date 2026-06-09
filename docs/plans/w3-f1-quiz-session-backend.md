# W3-F1 — Quiz Session Creation Backend

**Feature:** [`docs/features/w3-f1-quiz-session-backend.md`](../features/w3-f1-quiz-session-backend.md)
**Spec:** `days_11_15_features.md` §1 (Day 11)
**Depends on:** W2-F7 (Alembic chain on test-management-service — sessions table lands as `0004`), W2 Compose topology (question-management-service + Mongo healthy for the cross-service call), W2-F5 (question bank seeded so `$sample` returns rows)
**Unblocks:** W3-F2 (scoring/locking — needs `sessions` + `current_index` + `question_ids`), W3-F3 (frontend skeleton — calls `POST /sessions` server-side on load)

## User decisions (locked)

1. **Persist sampled question IDs.** Add a `question_ids` JSON column to `sessions` beyond the spec's 8 listed columns. The set is sampled once at creation, stored as an ordered list; `current_index` indexes into it. Required for W3-F2 advance and W3-F3 navigation to be coherent (re-sampling per-question would change the question set mid-exam).
2. **Strip answer fields from the session response.** The first question returned to the candidate omits `correct_answers` and `sample_answer`. Scoring stays server-side (W3-F2). Prevents reading answers from the network response / initial HTML.

## Context

`POST /sessions` in test-management-service mints an opaque session token, records **server-authoritative** timing, samples a fixed question set from question-management-service (QMS) over httpx, and returns the first (sanitized) question. This is the **first cross-service call in the platform** — the `httpx.AsyncClient` singleton + timeout / bounded-retry / correlation-id pattern set here is reused by W3-F4's draft endpoint and the W4 reporting service.

**What exists now:**
- test-management-service schema is owned by Alembic (`alembic/versions/0001..0003`); `init_db()` is connectivity-check only; `start.sh` runs `alembic upgrade head` before boot. New table = `alembic revision --autogenerate` → `0004`.
- Vertical-slice convention: `schemas/` → `repositories/` → `services/` → `v1/routes/`, routers included with prefix `/v1/api` in `main.py`.
- Correlation-id infra: `CorrelationIdMiddleware` sets a ContextVar; `src/utils/logging_config.get_correlation_id()` reads it. `src/utils/dependencies.py` already forwards it on an outbound httpx call — mirror that.
- `httpx` is in `requirements.txt`. `tests/` dir exists (CI runs `pytest --cov`).
- Gateway `ROUTES` (`services/api-gateway-service/main.py`) is an ordered regex table; new routable prefixes must be added.
- QMS exposes question CRUD/filter routes but **no `$sample` endpoint** — one must be added (detail-doc Note confirms).

**Key constraints / gotchas:**
- `Test.duration` is a SQLAlchemy `Interval` (`timedelta`), **not** `duration_seconds` as the spec prose says. Compute `expires_at = server_now + test.duration`; fall back to a default window (3600 s) when `duration` is null.
- Codebase stores **tz-naive UTC** datetimes (`datetime.utcnow()`, `_strip_timezone_from_dict`). `server_now` / `expires_at` follow that convention.
- Shared `eval_ai_dev` DB: Alembic `include_object` already filters to this service's tables, so `0004` autogen won't touch `users`. Keep the model registered in **both** `src/db/session.py` and `alembic/env.py` import lists.
- QMS `QuestionResponse` includes `correct_answers` / `sample_answer`; the sample endpoint may return them (internal), but test-management-service strips them before responding to the client (decision 2).

## Sessions table (`0004`)

| Column | Type | Notes |
|---|---|---|
| `session_id` | UUID PK | `uuid4()` |
| `test_id` | Integer FK → `tests.id` | |
| `user_id` | Integer | from `X-User-Id` (gateway-injected) |
| `session_token` | String, unique, indexed | `secrets.token_hex(32)` (opaque) |
| `server_now` | DateTime (naive UTC) | set server-side at creation |
| `expires_at` | DateTime (naive UTC) | `server_now + duration` |
| `status` | Enum `active`/`submitted`/`expired` | default `active` |
| `current_index` | Integer | default `0` |
| `question_ids` | JSON (list[str]) | ordered sampled Mongo `_id`s (decision 1) |
| `created_at` / `updated_at` | DateTime | match repo convention |

`SessionStatus` is a `str, enum.Enum` (`ACTIVE`/`SUBMITTED`/`EXPIRED`) mirroring `SubmissionStatus`.

## Response contract (locked early — W3-F3 consumes it server-side)

```jsonc
{
  "session_id": "<uuid>",
  "session_token": "<hex>",
  "server_now": "<iso8601>",
  "expires_at": "<iso8601>",
  "current_index": 0,
  "total_questions": 20,
  "question": {                 // sanitized — NO correct_answers / sample_answer
    "id": "<mongo _id>",
    "type": "mcq",
    "question_text": "...",
    "options": [{"option_id": 1, "text": "..."}, ...],
    "difficulty": "medium",
    "image_url": null
  }
}
```

## Step 0 — Branch & commit workflow

- **Pre-flight:** working tree has an uncommitted `docs/features/w2-f4-ci-quality-gates.md`. Inspect it; commit it to `richardh` if it's intended work, otherwise stash — do **not** carry an unrelated change onto the feature branch.
- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W3F1`** off `richardh` before any code change. Confirm with `git branch --show-current`.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — Sessions model + Alembic `0004`
- `src/models/session.py` — `Session` model + `SessionStatus` enum, columns per the table above. `question_ids` via `sqlalchemy.JSON`.
- Register the model in `src/db/session.py` `init_db()` imports **and** `alembic/env.py` imports (both lists kept in sync, per their docstrings).
- Generate the migration against a live/scratch DB:
  `alembic revision --autogenerate --rev-id 0004 -m "Add sessions table"` (from `services/test-management-service/`). Review the emitted op — must create only `sessions` (the `include_object` filter excludes `users`).
- **Commit:** `feat(w3-f1): add sessions model + alembic 0004 migration`

### M2 — `$sample` endpoint in question-management-service
- `src/repositories/question_repository.py` — `sample(size: int) -> list[Question]` using Beanie aggregation `Question.aggregate([{"$sample": {"size": size}}], projection_model=Question).to_list()`.
- `src/services/question_service.py` — `sample_questions(size)` wrapping the repo call (clamp `size` to a sane max, e.g. 100).
- `src/v1/routes/question_routes.py` — `GET /sample?size=N` returning `list[QuestionResponse]` via `_to_response`. **Declare it before `/{id}`** so the path param doesn't capture `sample` (same ordering caveat the file already calls out for `/presigned-upload-url`).
- **Commit:** `feat(w3-f1): add $sample endpoint to question-management-service`

### M3 — httpx client singleton + cross-service fetch
- `src/utils/question_client.py` — module-level `httpx.AsyncClient` singleton with explicit `timeout` (connect/read). `async def sample_questions(size)`:
  - calls `GET {QUESTION_SERVICE_URL}/v1/api/questions/sample?size={size}`,
  - forwards `X-Correlation-Id: get_correlation_id()` (step 4),
  - **bounded retries** (e.g. 2 retries on `httpx.TransportError` / 5xx with a short backoff; never retry 4xx),
  - returns parsed question dicts; raises a typed error on exhaustion.
  - `aclose()` helper for shutdown.
- **Commit:** `feat(w3-f1): add httpx question-service client (timeout, retries, correlation-id)`

### M4 — Session vertical slice + `POST /sessions`
- `src/schemas/session_schema.py` — `SessionCreate` (`test_id: int`), `SanitizedQuestion`, `SessionOut` (the response contract above).
- `src/repositories/session_repository.py` — `create(...)`, `get_by_id`, `get_by_token` (async, mirror `test_submission_repository`).
- `src/services/session_service.py` — `create_session(db, test_id, user_id)`:
  1. fetch test (`TestService`/`TestRepository`); **404** if missing.
  2. `server_now = datetime.utcnow()`; `expires_at = server_now + (test.duration or timedelta(seconds=3600))`.
  3. `session_token = secrets.token_hex(32)`; `session_id = uuid4()`.
  4. sample `test.number_of_questions or 20` questions via `question_client`; extract ordered `question_ids`; keep the first.
  5. persist the row **before** responding.
  6. build `SessionOut` with the **sanitized** first question (drop `correct_answers`/`sample_answer`).
- `src/v1/routes/session_route.py` — `router = APIRouter(prefix="/sessions", tags=["Sessions"])`; `POST /` (201) depends on `get_current_user_from_headers` for `user_id`; ValueError→404, upstream failure→502/503.
- `main.py` — include `session_router` with prefix `/v1/api`; add a `shutdown` event calling `question_client.aclose()`.
- **Commit:** `feat(w3-f1): implement POST /sessions with cross-service question fetch`

### M5 — Wiring: settings, compose env, gateway route
- `src/config/settings.py` — add `QUESTION_SERVICE_URL: str = "http://question-management-service:8003"`.
- `docker-compose.yml` — add `QUESTION_SERVICE_URL: http://question-management-service:8003` to test-management-service env; add `question-management-service: condition: service_healthy` to its `depends_on` (the call needs QMS up).
- `services/api-gateway-service/main.py` `ROUTES` — add `{"pattern": r"^/v1/api/sessions(/.*)?$", "service": "test-management-service"}`.
- **Commit:** `feat(w3-f1): wire QUESTION_SERVICE_URL + gateway /sessions route`

### M6 — Tests, requirements review, docs
- `tests/test_session_service.py` — unit tests with the QMS client and repo mocked: server-authoritative timing (expires_at = server_now + duration), token/uuid minting, question_ids persisted, **answer fields stripped** from the response, 404 on missing test. (Mirror existing `test_*_service.py` style.)
- Optional `tests/test_session_schema.py` if schema validation is non-trivial.
- Requirements review (see below); update detail doc + FEATURE_STATUS.md.
- **Commit:** `test(w3-f1): session service unit tests` and `docs(w3-f1): mark feature complete + evidence`

## Testing & validation

- **Unit (pass bar = green):** from `services/test-management-service/` → `pytest --cov` (existing suite + new session tests pass).
- **QMS lint/import:** from `services/question-management-service/` → `pytest` if present; otherwise import-check the new route.
- **Migration:** `alembic upgrade head` from `services/test-management-service/` against a scratch Postgres applies `0004` cleanly; `alembic downgrade -1` reverses it.
- **Smoke (`docker compose up --build`):**
  1. all services healthy; `sessions` table exists.
  2. login → obtain JWT → `POST /v1/api/sessions {"test_id": <seeded>}` through the gateway → **201** with the full contract; `question` carries no `correct_answers`/`sample_answer`.
  3. `expires_at - server_now` equals the test duration; row present in Postgres with `question_ids` populated and `current_index = 0`.
  4. grep logs across test-management-service **and** question-management-service for the same `correlation_id` on the one request (W2-F3 traceability).

## Requirements review (final milestone)

Re-read the detail-doc Steps 1–6 + spec §1 Implementation Details against the actual diff; confirm each with evidence (file:line / commit):
1. sessions table + `0004` migration · 2. `POST /sessions` handler (uuid4/token_hex, server-side expires_at, persist-before-respond) · 3. httpx singleton + `$sample` fetch + bounded retries · 4. correlation-id propagation · 5. response contract (sanitized) · 6. gateway route.
Then check off the detail-doc steps with evidence and flip the FEATURE_STATUS.md row to ✅ Completed, in this branch.

## Push gate

Push `richardh-feat-W3F1` to origin **only if** all tests pass **and** every Step 1–6 is confirmed. Otherwise stop, leave the branch local, report what's outstanding.

## Risks / watch-items

- **Empty question bank** → `$sample` returns fewer than requested. Decide behaviour: proceed with what's available, or 422 if zero. Plan: 422 when zero questions, otherwise use the sampled subset (log the shortfall).
- **QMS down at session creation** → surface as 502/503, not a 500; bounded retries first.
- **`Interval` vs `duration_seconds`** naming mismatch (handled: use `duration`, fallback 3600 s).
- Scope guard: scoring, answer submission, locking, and the draft endpoint are **W3-F2/W3-F4** — not in this branch.
