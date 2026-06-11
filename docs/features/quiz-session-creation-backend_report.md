# Adversarial Code Review — Quiz Session Creation Backend (W3-F1)

| | |
|---|---|
| **Feature** | Quiz Session Creation Backend |
| **Branch** | `jorge-qz-sess-backend` |
| **Base** | `main` @ `e4a3e55` |
| **Scope** | `services/test-management-service` (new quiz session model/schema/repo/service/route), `services/api-gateway-service/main.py` (route table) |
| **Review type** | Adversarial — precision finders + security/integrity attack passes, each finding independently verified |

---

## Files under review

- `services/test-management-service/src/models/quiz_session.py` (new)
- `services/test-management-service/src/schemas/quiz_session_schema.py` (new)
- `services/test-management-service/src/repositories/quiz_session_repository.py` (new)
- `services/test-management-service/src/services/quiz_session_service.py` (new)
- `services/test-management-service/src/v1/routes/quiz_session_route.py` (new)
- `services/test-management-service/tests/test_quiz_session.py` (new)
- `services/test-management-service/main.py` (router include)
- `services/test-management-service/src/config/settings.py` (`QUESTION_SERVICE_URL`)
- `services/api-gateway-service/main.py` (`/v1/api/sessions` route)

---

## Verdict

**Feature is NOT functional as written.** Two CONFIRMED blockers prevent it from working at all:

1. Every `POST /v1/api/sessions` call fails — the question fetch hits an endpoint that rejects the request with `400`.
2. The new unit test suite has a failing test (`1 failed, 3 passed`), so the CI coverage gate / test step is red.

Beyond the blockers, three HIGH security findings (missing authorization, IDOR, answer persistence) and several medium/low items are documented below.

---

## Findings (severity-ranked)

### 🔴 C1 — Session creation always fails: `/filter` called with no filter criterion
**File:** `src/services/quiz_session_service.py:59`
**Status:** CONFIRMED

`_fetch_questions` issues:

```python
GET /v1/api/questions/filter?limit=200
```

But `question-management-service` rejects a filter request that supplies none of `type` / `skill` / `difficulty` / `tags`:

```python
# question_service.py:375
if not any([question_type, skill, difficulty, tags]):
    raise HTTPException(status_code=400, detail="At least one filter parameter must be provided")
```

The `400` is caught at `quiz_session_service.py:69` and re-raised as `503`. **Result: 100% of session-creation requests fail.** Not covered by tests because `_fetch_questions` is mocked.

**Fix options:**
- Call `GET /v1/api/questions/` (returns all questions) and sample locally. Note: that route currently takes no `limit` param, so sampling must be done client-side.
- Or add a question-service endpoint for random sampling (`$sample`) as the original plan (`days_11_15_features.md`) specified.
- Or pass an always-true filter (e.g. iterate difficulties) — least clean.

---

### 🔴 C2 — Unit test fails: `TestSubmission` mapper not resolvable
**File:** `tests/test_quiz_session.py` (test `test_create_session_returns_start_response`)
**Status:** CONFIRMED (observed `1 failed, 3 passed` in actual pytest run)

Constructing `QuizSession(...)` triggers SQLAlchemy mapper configuration for the whole `Base` registry. `Test` declares `relationship("TestSubmission", ...)`, but `TestSubmission` is never imported in the test module, so:

```
sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[Test(tests)],
expression 'TestSubmission' failed to locate a name ('TestSubmission').
```

**Fix:** import all model modules at the top of the test (or in `conftest.py`) before any ORM class is instantiated:

```python
import src.models.skill        # noqa: F401
import src.models.test          # noqa: F401
import src.models.test_skill    # noqa: F401
import src.models.test_submission  # noqa: F401
import src.models.quiz_session  # noqa: F401
```

---

### 🟠 H1 — No authorization: any participant can start a session for any test
**File:** `src/services/quiz_session_service.py:101`
**Status:** CONFIRMED

`TestRepository.get_by_id()` returns the test with no check that:
- `test.active` is `True` (inactive/archived tests are startable), or
- the test is actually assigned to `current_user["id"]`.

Any authenticated participant can mint sessions for arbitrary `test_id`s, including tests never assigned to them.

**Fix:** reject when `test.active` is false; verify an assignment (`TestSubmission` for this `user_id` + `test_id`) exists before creating the session.

---

### 🟠 H2 — IDOR: `submission_id` accepted without ownership check
**File:** `src/services/quiz_session_service.py:117`
**Status:** CONFIRMED

`payload.submission_id` is stored straight into the FK with no validation that the submission belongs to `current_user["id"]`. A participant can attach their session to another participant's submission row.

**Fix:** if `submission_id` is provided, load it and assert `submission.user_id == current_user["id"]` (else `403`).

---

### 🟠 H3 — Correct answers persisted in `snapshot_json`
**File:** `src/models/quiz_session.py:51` / `src/services/quiz_session_service.py` (snapshot build)
**Status:** CONFIRMED (defense-in-depth)

The full question dict — including `correct_answers` and `answer_explanation` — is stored verbatim in `quiz_session_questions.snapshot_json`. The first-question response is correctly stripped via `_strip_correct_answers`, so **no leak today**. But the answers now live in test-management Postgres, and any future read endpoint that returns `QuizSessionQuestion` (e.g. "get question N") will leak them unless it re-strips.

**Fix:** store a sanitized snapshot (drop `correct_answers` / `answer_explanation` / `sample_answer`), OR keep a separate non-served column for grading and never serialize the raw snapshot to clients. Add a regression test asserting no answer fields cross the API boundary.

---

### 🟡 M1 — Schema creation depends on fragile implicit import; no Alembic
**File:** `src/db/session.py:50`
**Status:** CONFIRMED (works now, fragile)

`init_db()` runs `Base.metadata.create_all`. Its comment says "Import all models here" but **no imports follow**. The new tables get created only because `main.py` → `quiz_session_route` → `quiz_session_service` → `quiz_session` models are imported at module load before the startup hook fires. Reorder/refactor those imports and `create_all` silently skips the tables → `relation "quiz_sessions" does not exist` at first request. The W3-F1 plan called for an Alembic migration; none exists.

**Fix:** add explicit `from src.models.quiz_session import QuizSession, QuizSessionQuestion  # noqa: F401` inside `init_db()` before `create_all`, and/or introduce the Alembic migration the plan specified. `create_all` also never ALTERs existing tables — a real migration path is needed before any schema change ships.

---

### 🟡 M2 — No rate limit on session creation
**File:** `src/services/quiz_session_service.py:95-162`
**Status:** PLAUSIBLE (DoS surface)

Each `POST /sessions` performs a DB insert plus an outbound httpx call to question-service. No throttle → an authenticated participant can spam session creation, exhausting rows and hammering the question service.

**Fix:** per-user rate limit (e.g. middleware or a small token bucket); bound concurrent active sessions per user.

---

### 🔵 L1 — Redundant UUID default
**File:** `src/models/quiz_session.py:21`
The column has `default=uuid.uuid4` while the service always passes `session_id=uuid.uuid4()` explicitly. Two generation sites; ORM-bypassing inserts would use a different one. Pick one source of truth.

### 🔵 L2 — Pydantic v2 deprecation
**File:** `src/schemas/quiz_session_schema.py:29`
`class Config` raises `PydanticDeprecatedSince20` (errors in v3). Replace with `model_config = ConfigDict(from_attributes=True)`.

### 🔵 L3 — Duplicate env setup in test
**File:** `tests/test_quiz_session.py:16`
The `os.environ.setdefault(...)` block duplicates `conftest.py:6-13` (conftest runs first). Remove the duplicate.

### 🔵 L4 — `updated_at` has no `onupdate`
**File:** `src/models/quiz_session.py:36`
`default=datetime.utcnow` but no `onupdate=`, so the column never refreshes on mutation. `test_submission.py:40` uses the correct pattern. Add `onupdate=datetime.utcnow`.

---

## Verified-safe (attempted, no issue)

- `/v1/api/sessions` is **not** in `PUBLIC_PATH_PREFIXES` — JWT required. ✅
- `session_token` = `secrets.token_urlsafe(32)` (256-bit) and is **not** logged (the `logger.info` extra dict carries `session_id`, not the token). ✅
- Transaction ordering: question fetch precedes the row insert; `get_db` context manager rolls back on exception → snapshot inserts are atomic with the session row. ✅
- `random.sample(pool, n)` guarded by `len(pool) >= n` with full-pool fallback. ✅
- tz-aware `expires_at`/`server_started_at` set from `datetime.now(timezone.utc)`; naive `utcnow` defaults are overridden by the service. ✅

---

## Acceptance-criteria check (from `w3_features.md`)

| Criterion | Status |
|---|---|
| `POST /v1/api/sessions` creates a durable row with server-owned timing | ❌ blocked by C1 |
| Response includes first question without correct answers | ⚠️ response is stripped, but answers persisted server-side (H3) |
| Outbound call has timeout + correlation/request ID propagation | ✅ 10s timeout, `X-Correlation-Id`/`X-Request-Id` forwarded |
| Missing test returns 404 | ✅ tested |
| Empty question pool returns clear 503/424 | ✅ tested (503) — but unreachable in practice due to C1 |

---

## Recommended fix order

1. **C1** — make the question fetch hit a working endpoint (unblocks the whole feature).
2. **C2** — fix the failing test (unblocks CI).
3. **H1 / H2 / H3** — authorization, IDOR, answer persistence.
4. **M1** — explicit model import in `init_db` (+ plan an Alembic migration).
5. **M2 / L1–L4** — hardening and cleanup.

---

## Remediation applied (this branch)

| ID | Fix | File |
|---|---|---|
| C1 | Question fetch switched from `/questions/filter` (rejects no-criterion) to `/questions/` (list-all), then sampled locally | `quiz_session_service.py:_fetch_questions` |
| C2 | All model modules imported in test before any ORM instantiation | `tests/test_quiz_session.py` |
| H1 | Reject session creation for inactive tests → `403` | `quiz_session_service.py` |
| H2 | Supplied `submission_id` validated against `user_id` + `test_id` → `404`/`403` | `quiz_session_service.py` |
| H3 | Snapshot documented as server-only/sensitive; `_SENSITIVE_QUESTION_FIELDS` constant + regression test asserting served question carries no answer fields | `quiz_session_service.py`, `tests/test_quiz_session.py` |
| M1 | Explicit `import src.models.*` in `init_db()` before `create_all` | `db/session.py` |
| M2 | Coarse per-user active-session cap (`_MAX_ACTIVE_SESSIONS_PER_USER = 25`) → `429` | `quiz_session_service.py`, `quiz_session_repository.py` |
| L1 | Single UUID source — explicit generation in service; column default removed | `quiz_session_service.py`, `models/quiz_session.py` |
| L2 | `class Config` → `model_config = ConfigDict(from_attributes=True)` | `schemas/quiz_session_schema.py` |
| L3 | Duplicate `os.environ.setdefault` block removed (conftest is authoritative) | `tests/test_quiz_session.py` |
| L4 | `updated_at` given `onupdate=datetime.utcnow` | `models/quiz_session.py` |

**Notes / deferred:**
- **H3 design decision:** correct answers are intentionally retained in `snapshot_json` because the Feature 2 scoring engine needs a server-authoritative answer source. The fix guarantees they are never serialized to a client (no read endpoint exists; the only client payload is `QuizQuestionOut`, which structurally cannot hold answers) and adds a regression test. When a "get question N" endpoint is added in Feature 2/3, it must re-strip.
- **M1 / Alembic:** explicit imports make `create_all` reliable for local/dev. A real Alembic migration is still required before production schema evolution — tracked as part of the W3-F1 cross-week dependency, not done here.
- **M2:** the cap is a coarse infra-free guard, not true rate limiting. Real throttling (per-IP/per-token, sliding window) is a separate concern.

**Verification:**
- `pytest`: **30 passed** (8 in `test_quiz_session.py`, incl. new 403/404/429/H3 cases).
- `ruff check services/test-management-service`: **All checks passed.**
- Coverage: **72.44%** total (gate ≥70%); new quiz-session modules 86–100%.
