# Feature: Scoring Engine with Exact-Match & Partial-Credit Algorithms (W3-F2)

| | |
|---|---|
| **Feature** | Scoring Engine + safe answer submission |
| **Service** | `test-management-service` |
| **Branch** | `jorge-qz-sess-backend` |
| **Depends on** | W3-F1 (Quiz Session Creation Backend) — sessions, `session_id`, `current_index`, per-session question snapshots |
| **Status** | Implemented + unit-tested (working tree, not yet committed) |

---

## Goal

Add deterministic, side-effect-free scoring for single-select, true/false, and multi-select questions, then wire it into a transactionally safe answer-submission endpoint that enforces the session state machine, locks against concurrent retries, and is idempotent.

---

## Step-by-step implementation

### Phase 1 — Pure scoring module (no DB, no I/O)

1. **`src/scoring/types.py`** — `ScoreResult` frozen dataclass: `earned`, `possible`, `is_correct`, `details`.
2. **`src/scoring/exact_match.py`** — `score_exact_match(correct, submitted)`: set equality → `earned = 1.0` else `0.0`. Used for `mcq` and `true_false`.
3. **`src/scoring/partial_credit.py`** — `score_partial_credit(correct, submitted)`: `earned = clamp((tp - fp) / |correct|, 0, 1)`; `is_correct` only on exact set match; records `tp/fp/fn` in `details`.
4. **`src/scoring/__init__.py`** — `score_question(question_type, correct, submitted)` dispatch (`mcq`/`true_false` → exact, `multi` → partial, `text` → non-auto-scored zero-possible, unknown → `ValueError`).
5. **`tests/test_scoring.py`** — parametrized exact + partial matrices, dispatch, case-insensitivity, audit counts, text/unknown handling. Written before the route wiring.

### Phase 2 — Persistence

6. **`src/models/quiz_answer.py`** — `quiz_answers` table: one scored row per question, `UniqueConstraint(quiz_session_id, question_index)` to make double-scoring impossible at the DB level.
7. **`src/models/idempotency_key.py`** — `idempotency_keys` table: `key`, `quiz_session_id`, `request_hash` (sha256 of canonical body), `response_json`, `UniqueConstraint(quiz_session_id, key)`.
8. **`src/db/session.py`** — register both new models in `init_db()` so `create_all` builds the tables.

### Phase 3 — Repositories

9. **`src/repositories/quiz_session_repository.py`** — add `get_for_update()` (`SELECT … FOR UPDATE` row lock).
10. **`src/repositories/quiz_answer_repository.py`** — `add()`, `get_by_session_and_index()`.
11. **`src/repositories/idempotency_repository.py`** — `get(session_id, key)`, `add()`.

### Phase 4 — Schemas

12. **`src/schemas/quiz_session_schema.py`** — `AnswerSubmit` (`session_token`, `question_id`, `answers`) and `AnswerAck` (`question_id`, `recorded`, `current_index`, `status`, `finished`, `next_question`). `AnswerAck` deliberately omits score/correctness.

### Phase 5 — Service (state machine)

13. **`src/services/quiz_answer_service.py`** — `submit_answer()` orchestration:
    1. Lock session (`get_for_update`); 404 if absent.
    2. Authorize: `user_id` ownership + `session_token` match (403).
    3. Idempotency check *before mutation*: same key + same hash → replay stored `response_json`; same key + different hash → 409.
    4. Reject `submitted`/`expired` (409); expire-on-read if `expires_at <= now` (set `expired`, commit, 409).
    5. Locate the submitted question in the session snapshot set (422 if not present).
    6. Enforce `question_index == current_index` (out-of-order / already-answered → 409).
    7. Score against the snapshot's `correct_answers`.
    8. Persist `QuizAnswer`.
    9. Advance `current_index`; finalize → `submitted` + `submitted_at` on the last question.
    10. Store the idempotency record, commit, return `AnswerAck`.

### Phase 6 — Route

14. **`src/v1/routes/quiz_session_route.py`** — `POST /sessions/{session_id}/answer`, `Idempotency-Key` header required (400 if missing), guarded by `get_current_participant`.
15. **Gateway** — no change required: existing `^/v1/api/sessions(/.*)?$` already routes the sub-path.

### Phase 7 — Tests

16. **`tests/test_quiz_session_answers.py`** — service-level (mocked DB/repos, real scoring): advance, finalize, idempotent replay, key-reuse 409, submitted/expired 409, 404, ownership/token 403, out-of-order 409, unknown-question 422.

---

## Summary of changes & reasoning

| File | Change | Reasoning |
|---|---|---|
| `src/scoring/types.py` | `ScoreResult` dataclass | Single immutable result shape; `details` keeps scoring auditable for later reporting. |
| `src/scoring/exact_match.py` | Set-equality scorer | Single-select/true-false are all-or-nothing; set comparison handles extra/missing selections uniformly. |
| `src/scoring/partial_credit.py` | `(tp-fp)/|correct|` clamped | Rewards correct picks, penalizes wrong ones so "select everything" scores 0, not full marks. Pure + deterministic = trivially unit-testable. |
| `src/scoring/__init__.py` | `score_question` dispatch | One entry point; type→algorithm mapping isolated from the service. |
| `src/models/quiz_answer.py` | `quiz_answers` table | Durable per-question score; unique (session,index) is a DB-level double-score guard independent of app logic. |
| `src/models/idempotency_key.py` | `idempotency_keys` table | Stores the prior response keyed by (session,key); `request_hash` distinguishes a true retry from key reuse. |
| `quiz_session_repository.get_for_update` | Row lock | Pessimistic lock serializes concurrent tabs/retries so `current_index` can't race. |
| `quiz_answer_repository`, `idempotency_repository` | CRUD | Keep DB queries out of the service, matching the repo/service split used across the codebase. |
| `quiz_session_schema.AnswerAck` | No score in response | Returning `is_correct`/`earned` per question would let a candidate brute-force answers mid-test. Score recorded server-side only. |
| `quiz_answer_service.submit_answer` | State machine | Centralizes locking, idempotency, ordering, scoring, finalization in one transaction. |
| `quiz_session_route` answer endpoint | `Idempotency-Key` required | Mutation safety contract for the frontend; 400 makes the requirement explicit. |
| `db/session.init_db` | Register new models | `create_all` only builds imported models; explicit import keeps table creation reliable (matches F1 fix). |

**Key design decisions**

- **Snapshot as the scoring source.** Correct answers come from the per-session question snapshot (frozen at session creation), not a live Mongo re-fetch, so editing a question mid-exam can't change a candidate's grade.
- **Server-authoritative ordering.** Answers must arrive for `current_index`; the frontend can navigate freely in local state but the backend owns progression.
- **Idempotency hash is order-independent** (answers sorted before hashing) so `[1,3]` and `[3,1]` are the same request.
- **Expire-on-read** commits the `expired` transition so a stale session is cleaned up the moment it's touched.

---

## Roadblocks & issues during testing (and fixes)

| # | Issue | Root cause | Fix |
|---|---|---|---|
| 1 | `test_missing_session_returns_404` raised `AttributeError`, not `HTTPException` | Test helper read `session.session_id` while passing `session=None` for the not-found case | Guard in helper: use a literal UUID when `session is None` |
| 2 | Ruff `I001` import-sort failures on 5 new files | New imports not in ruff's canonical order | `ruff check --fix` (import ordering only; no semantic change) |
| 3 | SQLAlchemy mapper error risk in tests | Instantiating `QuizAnswer`/`IdempotencyKey` triggers full mapper config; `Test`→`TestSubmission` relationship resolves by name | Import all model modules at the top of the test file before any ORM instantiation (lesson carried from F1) |
| 4 | `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning | Starlette renamed the constant | Left as-is — matches the constant used elsewhere in the codebase; cosmetic, non-failing. Flagged for a repo-wide sweep later |
| 5 | Risk of `session_id`/UUID being unset under mocked flush | (Carried from F1) relying on a column default means the value only materializes at real DB flush | Service generates `session_id` explicitly; not re-introduced here |

No production-code bugs surfaced during testing beyond the test-harness issue (#1); the scoring functions and state machine passed on the first full run after the harness fix.

### Adversarial review findings & fixes applied

An adversarial review pass (correctness + security + concurrency finders, each verified) ran after the initial implementation. Applied fixes:

| ID | Finding | Severity | Fix |
|---|---|---|---|
| S1 | `score_exact_match` awarded `earned=1.0` for empty-vs-empty (`correct=[]`/`None`, `submitted=[]`) | 🟠 correctness | `is_correct = bool(correct_set) and submitted_set == correct_set`; added parametrized test |
| S2 | `session_token` compared with `!=` (timing oracle) | 🟠 security | `hmac.compare_digest` |
| S3 | `AnswerSubmit.answers` had no length cap (large-payload DoS) | 🟡 hardening | `Field(..., max_length=50)` |
| S4 | Whitespace-only `Idempotency-Key` passed the `if not key` check | 🟡 hardening | `.strip()` before the emptiness check |
| S5 | `QuizAnswerRepository.get_by_session_and_index` was dead code; an unhandled unique-constraint violation would surface as 500 | 🔵 robustness | Call it before scoring → clean 409 on a pre-existing answer; added test |

**Confirmed-but-not-fixed (documented as accepted):**
- *bool/int set collision* (`True == 1`): real in Python but benign — within a question type the frontend sends matching types, and submitting `True` for single-select option 1 simply selects option 1. Not exploitable.
- *duplicate single-select selection* (`[2,2]`): set-dedup scores it as selecting option 2, which matches grading intent.
- *text `possible=0.0`*: divide-by-zero risk lives only in future score aggregation (W4 results reporting); no consumer exists yet. Tracked in Deferred.

**Refuted:** `IntegrityError`→500 under concurrency — the `SELECT … FOR UPDATE` lock plus the ordering check serialize same-session submissions (the second request replays or hits a 409 before insert) on Postgres. S5 covers the non-Postgres / lock-not-honored edge.

Post-fix verification: **66 passed** (+4 new), ruff clean, coverage **74.89%**.

---

## Verification

- `pytest`: **62 passed** (24 new — 17 scoring, 11 answer state-machine incl. replay/409s/expiry/advance/finalize).
- `ruff check services/test-management-service`: **All checks passed.**
- Coverage: **74.85%** total (gate ≥70%). New code: scoring 100%, answer service 99%, models 100%; repositories 64% (`get`/`add` paths deferred to the real-Postgres integration tests planned in the next batch).

**Acceptance criteria (plan lines 282–287):** scoring pure ✓ · answer mutation transactionally safe ✓ · idempotent retries don't double-score ✓ · session state machine enforced ✓.

---

## Deferred / follow-ups

- Real-Postgres integration tests exercising the `SELECT … FOR UPDATE` race and the unique-constraint double-score guard (mocks can't prove DB-level locking).
- Repo-wide `HTTP_422_UNPROCESSABLE_ENTITY` → `…_CONTENT` sweep.
- Alembic migration for `quiz_answers` / `idempotency_keys` (same open item as F1's `create_all`-only gap).
