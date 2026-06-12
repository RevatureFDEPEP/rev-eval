# Secure Quiz-Taking Vertical Slice (W3)

## Decision Summary

Implemented a server-authoritative quiz-taking slice in `test-management-service`,
wired through the gateway and a new participant frontend flow. Timing, scoring,
answer storage, and attempt-locking all live on the server; the client is never
trusted for time, correctness, or attempt state.

Key decisions:

- **Single route contract.** Quiz sessions live under `/v1/api/sessions` (not the
  stale `/v1/api/test-sessions/*` the old frontend called). One contract, exposed
  by the gateway, consumed by the frontend.
- **Server-authoritative timing.** `expires_at` is computed from the server clock
  at session creation and every lock decision compares against `datetime.utcnow()`.
  The frontend countdown is derived from the server's `server_now`/`expires_at`,
  not a local-only clock.
- **No answer-key leakage.** The full question (with `correct_answers`) is
  snapshotted server-side for scoring and never serialized to a participant.
  Participant question views use a dedicated safe schema; the question service's
  read endpoints are role-gated.
- **Deterministic, pure scoring.** A side-effect-free `src/scoring/` module scores
  single-select, true/false (exact match), and multi-select (set-overlap partial
  credit). Trivially unit-testable.
- **Idempotent, locked answer submission.** Answer submits take a row-level lock
  on the session and honor an `Idempotency-Key`: same key + same payload replays
  the stored response; same key + different payload is rejected (409).
- **State machine.** Sessions are `in_progress → submitted | expired`. Submitted
  and expired sessions are immutable — draft saves and answer submits are rejected.
- **Portable column types.** `session_id` is a `String(36)` uuid and JSON payloads
  use the dialect-neutral `JSON` type, so the same models run on Postgres in
  production and in-memory SQLite in the test suite (real integration coverage).

## Route Contract

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/v1/api/sessions` | participant | Create durable session. Returns `server_now`, `expires_at`, `session_token`, `session_id`, `total_questions`, and the first question (no answer keys). |
| GET | `/v1/api/sessions/{id}` | participant (owner) | Full session state: timing, current index, buffered draft answers, all safe questions, scores once submitted. Overdue sessions report as `expired`. |
| PATCH | `/v1/api/sessions/{id}/draft` | participant (owner) | Autosave buffered answers and/or cursor. Rejected once submitted/expired. |
| POST | `/v1/api/sessions/{id}/answers` | participant (owner) | Score and record one answer. `Idempotency-Key` header supported. No per-question correctness in the response. |
| POST | `/v1/api/sessions/{id}/submit` | participant (owner) | Finalize and return the aggregate score. Idempotent. |

## Scoring Rules

| Type | Algorithm | Earned |
| --- | --- | --- |
| `mcq`, `true_false` | exact match | `1.0` iff submitted set == correct set, else `0.0` |
| `multi` | partial credit | `clamp((true_positives − false_positives) / |correct|, 0, 1)`; `is_correct` only on exact set match |
| `text` | not auto-scored | `possible = 0.0`, flagged for manual grading |

Empty-vs-empty never scores full marks. Options are 1-indexed positions.

## Security Boundaries

- **Answer-key gating (question service).** `QuestionPublic` (a new schema)
  drops `correct_answers`, `answer_explanation`, and `sample_answer`. List/detail/
  filter endpoints serialize the full `QuestionResponse` only for `TRAINER`/`ADMIN`
  callers (verified `X-User-Role` injected by the gateway); everyone else, and any
  request with no role, gets the safe view. The quiz session service's internal
  snapshot fetch is a trusted server-to-server call that identifies as `ADMIN`.
- **Header anti-spoof (gateway).** The gateway strips any client-supplied
  `X-User-*` headers before injecting the JWT-verified identity, so a caller can
  never smuggle a forged identity downstream — including through the
  unauthenticated legacy `/{service}/{path}` route.
- **Internal-port hardening (compose).** `user-service`, `question-management-service`,
  and `test-management-service` publish to `127.0.0.1` only. They trust
  gateway-injected `X-User-*`, so they must not be reachable off-host where the
  gateway boundary could be bypassed. The API gateway (`:8000`) is the public
  entry point; in-cluster traffic uses Docker DNS.
- **IDOR / ownership.** Session reads/writes require the caller to own the session
  (404 on mismatch, to avoid confirming another user's session). A supplied
  `submission_id` must belong to the caller and the test.

## Implementation Details

1. `src/scoring/` — pure scoring (`types`, `exact_match`, `partial_credit`,
   dispatch in `__init__`).
2. `src/models/quiz_session.py` — `QuizSession`, `QuizSessionQuestion` (server-only
   snapshot), `QuizAnswer` (latest scored answer per question),
   `IdempotencyRecord` (per-session idempotency ledger).
3. `src/schemas/quiz_session_schema.py` — create/start/state/draft/answer/submit
   schemas; participant-facing ones omit answer keys and per-question correctness.
4. `src/repositories/quiz_session_repository.py` — including a `with_for_update`
   locking read.
5. `src/services/quiz_session_service.py` — create (server timing, question
   sampling, IDOR guards, anti-abuse cap), get (lazy expiry), draft, idempotent
   locked answer submission, idempotent finalize.
6. `src/v1/routes/quiz_session_route.py` — the five endpoints; wired in `main.py`,
   `settings.py` (`QUESTION_SERVICE_URL`), and `db.init_db`.
7. Gateway — `/v1/api/sessions` route + `strip_client_identity_headers`.
8. Question service — `QuestionPublic` + role-aware serialization.
9. Frontend — `lib/api/quiz.ts` (new contract), `client.ts` (`patch` + per-call
   headers), BFF forwards `Idempotency-Key`/`X-Correlation-Id`, and a new
   server-backed take page at `participant/tests/take/quiz/[testId]`.
10. `docker-compose.yml` — loopback-only publishing for internal services.

## Tests

| Path | Covers |
| --- | --- |
| `test-management-service/tests/test_scoring.py` | exact/partial scoring + dispatch |
| `test-management-service/tests/test_quiz_session.py` | server timing/expiry, safe questions (no keys) while snapshot keeps keys, inactive-test + non-owner rejection |
| `test-management-service/tests/test_quiz_session_answers.py` | scoring recorded without leaking correctness, partial credit, idempotent retry, idem-key conflict, submitted + expired immutability, idempotent finalize, draft autosave persistence |
| `question-management-service/tests/test_answer_key_leak.py` | participant/anonymous views strip answer keys; trainer/admin retain them |

Real DB integration tests run against in-memory SQLite via the `async_session`
fixture (added `aiosqlite` to `services/requirements-dev.txt`).

### End-to-end (Playwright)

`frontend/e2e/quiz-happy-path.spec.ts` drives a real browser through the full
slice: a participant logs in, the take page mints a server-backed session, the
candidate answers every question under the server-driven countdown, submits, and
lands on the locked result screen — exercising browser → BFF → gateway →
test-management → question-management.

Run it against the live Compose stack:

```bash
# 1. Bring up the stack
docker compose up --build -d

# 2. Seed Postgres (users/tests/submissions) and the question bank
docker exec rev-eval-test-management python seed_db.py
#    Ensure the Mongo question bank is non-empty (mcq / true_false / multi).

# 3. Install the browser once, then run the test
cd frontend
pnpm exec playwright install chromium
pnpm test:e2e
```

The spec is parameterized via env vars (`E2E_BASE_URL`, `E2E_EMAIL`,
`E2E_PASSWORD`, `E2E_QUIZ_TEST_ID`, `E2E_CHANNEL`). It targets `http://localhost:3000`
by default. Because the Compose frontend runs `next dev`, timeouts are generous to
absorb first-hit route compilation. This flow was verified end-to-end against the
local stack (login → session → answer → submit → locked result).

A backend-only smoke of the same contract through the gateway also confirmed: no
`correct_answers` in participant question reads, server `server_now`/`expires_at`,
idempotent answer replay, `Idempotency-Key` conflict (409), no per-question
correctness in answer responses, aggregate score on submit, and a 409 on any
mutation after submission.

## Known Gaps

- The legacy two-part adaptive quiz API (`lib/api/quiz-sessions.ts`,
  `take/mcq/[testId]`) is left intact for trainer/results views; it is not part of
  this slice's contract.
- The Playwright happy-path runs against the live stack and is not yet wired into
  CI (it needs the full Compose stack + seeded data running).
- Scoring assumes auto-scorable types; `text` questions are flagged for manual
  grading and excluded from `max_score`.
