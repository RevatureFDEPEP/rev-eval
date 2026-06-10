# W3-F2 — Scoring Engine with Exact-Match & Partial-Credit + Attempt Locking

**Feature:** [`docs/features/w3-f2-scoring-engine-locking.md`](../features/w3-f2-scoring-engine-locking.md)
**Spec:** `days_11_15_features.md` §2 (Day 12)
**Depends on:** W3-F1 (✅ — `sessions` table, `session_id`, `current_index`, `question_ids` exist; `question_client` singleton + correlation-id pattern established), W2-F2 (✅ — pytest configured in test-management-service so the parameterized scoring tests run in CI)
**Unblocks:** W3-F4 (autosave/submit-lock — the session state machine + `PATCH /draft` base layer), W4-F1 (results reporting — needs populated `answers`), W4-F3 (role-based aggregate queries — `answers` data for `GROUP BY`/window fns), W4-F5 (tech-debt audit — scoring-algorithm ADR)

## User decisions (locked)

1. **Hide score from the answer response.** `POST /sessions/{id}/answer` persists `score` / `is_correct` to the `answers` table but does **not** return them. The response carries only advance state (`current_index`, `status`, `next_question`, `submitted_at`). Prevents a candidate inferring the answer key by probing mid-exam; W4-F1 reads scores from the DB.
2. **`Idempotency-Key` header is REQUIRED.** Missing/blank header → **422** before any scoring. Strict REST contract: every answer mutation must carry a client-generated key. Dedup table replays the stored response on retry.

## Context

W3-F1 mints sessions and returns the first sanitized question. W3-F2 adds the **answer-submission half**: a pure scoring core, then a transactional, idempotent, pessimistically-locked `POST /sessions/{id}/answer` that scores the current question, advances the state machine, and finalizes on the last question.

**What exists now:**
- `Session` model (`src/models/session.py`) — `SessionStatus(ACTIVE/SUBMITTED/EXPIRED)`, `current_index`, `question_ids` (ordered Mongo `_id` list), `server_now`/`expires_at` (tz-naive UTC). **No `submitted_at` column yet** — this feature adds it.
- `SessionRepository` — `get_test`, `create`, `get_by_id`, `get_by_token` (async).
- `question_client` (`src/utils/question_client.py`) — httpx singleton, `sample_questions(size)`, bounded retries on transient errors, `X-Correlation-Id` propagation, `aclose()`. **No single-question fetch yet** — this feature adds `get_question(qid)`.
- QMS `GET /v1/api/questions/{id}` returns `QuestionResponse` **including `correct_answers`** (`List[Union[int,bool,str]]`) — the scoring source of truth. Question types: `mcq` (single int option_id), `true_false` (single bool), `multi` (list of int option_ids), `text` (sample_answer; not auto-scorable).
- Alembic chain at `0004`; `start.sh` runs `alembic upgrade head` on boot; `init_db()` is connectivity-check only. New tables = `alembic revision --autogenerate` → `0005`.
- Gateway `ROUTES` already matches `^/v1/api/sessions(/.*)?$` → test-management-service (added in W3-F1). **No gateway change needed** — `/sessions/{id}/answer` is already routed.
- `get_current_user_from_headers` dependency yields `{id, email, role}` from gateway-injected `X-User-*`.
- pytest suite exists (`tests/`), driven with `asyncio.run()` + `AsyncMock` patches (no DB/network).

**Key constraints / gotchas:**
- tz-naive UTC everywhere (`datetime.utcnow()`); `submitted_at` follows suit.
- Shared `eval_ai_dev` DB: Alembic `include_object` filters to this service's tables, so `0005` autogen won't touch `users`. Register new models in **both** `src/db/session.py` and `alembic/env.py` import lists.
- `expire_on_commit=False` on the session factory — model attrs stay readable after `commit()`.
- Pessimistic lock requires a real transaction: `select(Session).where(...).with_for_update()` inside a single `db` scope, **no autocommit between read and write**.

## New schema (`0005`)

### `answers` table — one scored row per answered question
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `session_id` | UUID FK → `sessions.session_id` | |
| `question_id` | String | Mongo `_id` of the scored question |
| `question_index` | Integer | slot in `question_ids` this answers |
| `submitted_answers` | JSON | raw client payload (list) |
| `score` | Float | 0.0–1.0 (fraction; partial-credit aware) |
| `is_correct` | Boolean | `score == 1.0` |
| `created_at` | DateTime (naive UTC) | |
| | | **UniqueConstraint(`session_id`, `question_index`)** — one answer per slot |

### `idempotency_keys` table — dedup / response replay
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `idempotency_key` | String | client-supplied |
| `session_id` | UUID FK → `sessions.session_id` | scope key to its session |
| `status_code` | Integer | stored response status |
| `response_body` | JSON | stored response payload (replayed verbatim) |
| `created_at` | DateTime (naive UTC) | |
| | | **UniqueConstraint(`session_id`, `idempotency_key`)** |

### `sessions` — add column
- `submitted_at` `DateTime` nullable — set when status → `SUBMITTED`.

## Scoring core (`src/scoring/`)

`ScoreResult` (frozen dataclass, shared): `score: float` (0.0–1.0), `is_correct: bool`, `max_score: float = 1.0`. Pure, no DB/network — trivially unit-testable.

- **`exact_match.py`** — single-select (`mcq`, `true_false`). `score_question(question_type, correct_answers, submitted_answers) -> ScoreResult`: `set(submitted) == set(correct)` → `1.0`/`True`, else `0.0`/`False`. Empty submission → `0.0`.
- **`partial_credit.py`** — multi-select (`multi`). Same signature. **Jaccard index** `|correct ∩ submitted| / |correct ∪ submitted|` as `score`; `is_correct = (score == 1.0)` (full match). Empty correct set guarded. Penalizes wrong extra selections (they inflate the union).
- **Dispatch** (`__init__.py`): `score(question_type, correct_answers, submitted_answers)` routes `mcq`/`true_false` → exact_match, `multi` → partial_credit. `text` → not auto-scorable: `ScoreResult(0.0, False)` flagged for manual review (out of scope here; W4 concern) — recorded, never blocks advance.

**ADR note (for W4-F5):** Jaccard chosen over all-or-nothing and over "correct-minus-wrong" because it (a) gives graded partial credit, (b) symmetrically penalizes both missed and spurious selections, (c) is bounded [0,1] and order-independent. Capture rationale in the module docstring.

## Answer endpoint flow (`POST /sessions/{id}/answer`)

Request: path `session_id`; header `Idempotency-Key` (**required**); body `AnswerSubmit { submitted_answers: list }`.

Single transaction (`SessionService.submit_answer`):
1. **Require `Idempotency-Key`** — missing/blank → 422 (enforced at route via header param).
2. `SELECT ... FOR UPDATE` on the session row (`with_for_update()`) — concurrent retries queue here.
3. **Idempotency replay** — look up (`session_id`, key) in `idempotency_keys`; if present, return stored `(status_code, response_body)` without re-scoring.
4. **State gate** — `status != ACTIVE` → **409** (`submitted`/`expired` terminal). If `expires_at < utcnow()`: flip `status = EXPIRED`, commit, **409/410**.
5. **Resolve current question** — `qid = question_ids[current_index]`; fetch `correct_answers` via `question_client.get_question(qid)` (forwards correlation id, bounded retries; failure → 502).
6. **Score** — `scoring.score(qtype, correct_answers, submitted_answers)`.
7. **Persist `Answer`** row (UniqueConstraint guards a double-insert for the slot).
8. **Advance** — `current_index += 1`. If `current_index >= len(question_ids)`: `status = SUBMITTED`, `submitted_at = utcnow()`, `next_question = None`. Else fetch + sanitize the next question for the response.
9. **Store idempotency record** (key, status, response body) and **commit** once.

Response (`AnswerResult`, **score hidden**):
```jsonc
{
  "session_id": "<uuid>",
  "question_id": "<scored mongo _id>",
  "current_index": 1,            // advanced
  "total_questions": 20,
  "status": "ACTIVE",            // or "SUBMITTED"
  "submitted_at": null,          // iso when SUBMITTED
  "next_question": { /* SanitizedQuestion */ } // null when SUBMITTED
}
```

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W3F2`** off `richardh` before any code change. Confirm with `git branch --show-current`.
- **First commit on the branch = this plan file.**
- One commit per milestone below (Conventional Commits, matching repo history).

## Milestones

### M1 — Pure scoring module (Step 1)
- `src/scoring/__init__.py` — `ScoreResult` dataclass + `score(...)` dispatch.
- `src/scoring/exact_match.py`, `src/scoring/partial_credit.py` — pure `score_question(...)`, no imports of DB/httpx.
- ADR rationale in `partial_credit.py` docstring.
- **Commit:** `feat(w3-f2): pure exact-match + partial-credit (Jaccard) scoring module`

### M2 — Schema: models + Alembic `0005` (Steps 2–4 substrate)
- `src/models/answer.py` — `Answer` model (table above).
- `src/models/idempotency_key.py` — `IdempotencyKey` model (table above).
- `src/models/session.py` — add `submitted_at` column.
- Register both new models in `src/db/session.py` `init_db()` imports **and** `alembic/env.py` imports (keep lists in sync).
- Generate against a scratch/live DB: `alembic revision --autogenerate --rev-id 0005 -m "Add answers + idempotency_keys, sessions.submitted_at"` (from `services/test-management-service/`). Review emitted ops — must touch only `answers`, `idempotency_keys`, `sessions` (not `users`).
- Also add the two models to `tests/conftest.py` import list (relationship resolution).
- **Commit:** `feat(w3-f2): answers + idempotency_keys tables + submitted_at (alembic 0005)`

### M3 — Single-question fetch in question_client (Step 2 dep)
- `src/utils/question_client.py` — `async def get_question(qid: str) -> dict`: `GET /v1/api/questions/{qid}`, forwards `X-Correlation-Id`, same bounded-retry/transient handling as `sample_questions`, raises `QuestionServiceError` on exhaustion / non-retryable 4xx. 404 → typed not-found (caller maps to 404).
- **Commit:** `feat(w3-f2): add question_client.get_question single-fetch`

### M4 — Repos + schemas for answer/idempotency
- `src/repositories/session_repository.py` — `get_for_update(db, session_id)` (`with_for_update()`), `update(db, session)` (flush, no standalone commit — endpoint owns the txn).
- `src/repositories/answer_repository.py` — `create(db, answer)`.
- `src/repositories/idempotency_repository.py` — `get(db, session_id, key)`, `create(db, record)`.
- `src/schemas/session_schema.py` — `AnswerSubmit { submitted_answers: list }`, `AnswerResult` (response contract above; score-free).
- **Commit:** `feat(w3-f2): repositories + schemas for answer submission`

### M5 — Endpoint + service (Steps 2–4)
- `src/services/session_service.py` — `submit_answer(db, session_id, user_id, submitted_answers, idempotency_key)`: the transactional flow above (lock → idempotency replay → state gate → resolve question → score → persist answer → advance/finalize → store idempotency → commit). Typed exceptions: `SessionNotFound`, `SessionTerminalError` (→409), `SessionExpiredError` (→409). Reuse `EmptyQuestionBankError`/`QuestionServiceError` mapping.
- `src/v1/routes/session_route.py` — `POST /{session_id}/answer`: `Idempotency-Key` via `Header(...)` (required → 422 if absent), `get_current_user_from_headers`, map service exceptions to 404/409/422/502.
- **No gateway change** — `^/v1/api/sessions(/.*)?$` already routes here (verified `services/api-gateway-service/main.py:55`).
- **Commit:** `feat(w3-f2): POST /sessions/{id}/answer with lock, idempotency, state machine`

### M6 — Parameterized tests (Step 5)
- `tests/test_scoring.py` — pure-function matrix via `pytest.mark.parametrize`: exact-match (mcq correct/incorrect), true_false, full-match multi, partial Jaccard (subset, superset/spurious, disjoint, empty). Assert exact `score` + `is_correct`. No fixtures.
- `tests/test_answer_endpoint.py` — service-level with repos + `question_client` mocked (`AsyncMock`, `asyncio.run()` style):
  - happy path scores + advances `current_index`;
  - **idempotency**: same key replays stored response, scoring invoked once;
  - missing `Idempotency-Key` → 422;
  - **state machine**: answering a `SUBMITTED`/`EXPIRED` session → 409;
  - final question → `status=SUBMITTED`, `submitted_at` set, `next_question=None`;
  - **score hidden** from response body (assert keys absent).
  - (Real-Postgres concurrency/`FOR UPDATE` race is W3-F5; note the boundary.)
- **Commit:** `test(w3-f2): parameterized scoring + answer endpoint (lock/idempotency/state)`

### M7 — Requirements review + docs
- Re-read detail-doc Steps 1–5 + spec §2 acceptance criteria; verify each against the diff (file:line, commit).
- Update `docs/features/w3-f2-scoring-engine-locking.md` (✅ steps + evidence) and the `FEATURE_STATUS.md` W3-F2 row → ✅ Completed.
- **Commit:** `docs(w3-f2): mark feature complete + requirements review evidence`

## Testing & validation

- **Unit (pass bar = all green):** from `services/test-management-service/` → `pytest --cov`. Existing suite + new `test_scoring.py` + `test_answer_endpoint.py` pass; coverage not regressed.
- **Migration sanity:** `alembic upgrade head` then `alembic downgrade -1` on a scratch DB applies/reverts `0005` cleanly (drops both tables + the column + the enum is untouched).
- **Smoke (Compose):** `docker compose up --build` healthy; `POST /v1/api/sessions` then `POST /v1/api/sessions/{id}/answer` (with `Idempotency-Key`) via gateway → advances `current_index`; replaying the same key returns the identical body; answering past the last question yields `status=SUBMITTED` and a subsequent answer → 409; missing key → 422.
- Capture real output; never report a green bar not seen.

## Requirements review (final gate)

Map each detail-doc Step to evidence before pushing:
1. Pure scoring module (no DB/side effects) — `src/scoring/*`, `test_scoring.py`.
2. `POST /answer` + `SELECT FOR UPDATE` before reading `current_index` — `session_service.submit_answer`, `session_repository.get_for_update`.
3. `Idempotency-Key` + dedup table, replay without re-scoring — `idempotency_keys`, `idempotency_repository`, endpoint.
4. Advance `current_index`; final → `submitted` + `submitted_at`; further mutations 409; `submitted`/`expired` terminal — service state machine.
5. Parameterized pytest (exact/full/Jaccard/partial) + endpoint lock/idempotency/state — `test_scoring.py`, `test_answer_endpoint.py`.

## Push gate

Push `richardh-feat-W3F2` to origin **only if** `pytest --cov` is green **and** the requirements review confirms every Step. Otherwise stop, leave the branch local, report what's outstanding.
