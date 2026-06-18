# Technical Debt Inventory

A structured audit of shortcuts taken across Weeks 1–4 of the rev-eval build.
Each item records **where** it lives, the **condition under which it bites**
(it may be harmless at cohort scale and dangerous in production), and an
**urgency** rating. Verified against the `alexisc` integration branch on
2026-06-18.

Two of the consequential decisions behind these items are written up as ADRs:
- [ADR-0001 — Cross-service data access for reporting](adr/0001-cross-service-data-access-for-reporting.md)
- [ADR-0002 — Multi-select scoring algorithm](adr/0002-multi-select-scoring-algorithm.md)

## Ranked summary

| # | Debt | Urgency | Bites when |
|---|------|---------|-----------|
| 1 | Insecure default secrets in settings | **High** | Any deploy that doesn't override env → forgeable tokens / open object store |
| 2 | Per-service JWT not re-verified (gateway-trust) | **High** | An attacker can reach a service directly, bypassing the gateway |
| 3 | Reporting service unimplemented + no mirror sync | **High** | All W4 reporting features; blocks the results/dashboard slice |
| 4 | Active-session guard is not race-proof | Medium | Two concurrent "start quiz" POSTs → duplicate/re-rolled sessions |
| 5 | Tests mock the DB session; no real-DB integration tests | Medium | A bug in actual SQL / locking / migrations ships green |
| 6 | Answer-encoding coupling (1-indexed option_id) | Medium | Frontend submits 0-indexed/text → every multi-choice silently scores 0.0 |
| 7 | Dead / stale code (dashboard_route, legacy_gateway, two-part client) | Medium | Misleads the next developer; one route 404s through the gateway |
| 8 | No essay/`text` auto-scoring | Low | Essay/short-answer questions cannot be auto-graded (placeholder) |
| 9 | Magic values not centralized (pass threshold, page size) | Low | Trainer aggregates need a tunable pass threshold not yet config-driven |

## Detail

### 1. Insecure default secrets — **High**
- **Location:** `services/user-service/src/config/settings.py:20`
  (`JWT_SECRET = "change-me-in-production"`),
  `services/question-management-service/src/config/settings.py:40`
  (`S3_SECRET_KEY = "minioadmin"`).
- **Condition:** harmless in local dev where env vars are set. In any
  environment that ships the default, the JWT signing key is public knowledge →
  anyone can mint a valid trainer token; the object-store credential is the
  well-known MinIO default.
- **Repayment:** make the secret **required** (no default) so the app fails fast
  on a missing env var instead of silently running with a known key.

### 2. Per-service JWT not re-verified — **High**
- **Location:** `services/test-management-service/src/v1/routes/quiz_session_route.py:232`
  (comment: "per-service JWT re-verification is a follow-up"). Services trust the
  gateway-injected `X-User-*` identity headers.
- **Condition:** safe only as long as every service is unreachable except through
  the gateway. If a service port is exposed (compose, k8s misconfig), a caller
  can set `X-User-Role: TRAINER` headers directly and be trusted.
- **Repayment:** re-verify the Bearer JWT signature inside each service
  (defense-in-depth), which is exactly what W4-F3's `require_trainer` dependency
  introduces for the reporting service — generalize it.

### 3. Reporting service unimplemented + no mirror sync — **High**
- **Location:** `services/reporting-and-analytics-service/` (README only; not in
  `docker-compose`).
- **Condition:** blocks the entire W4 reporting/dashboard slice. Per
  [ADR-0001](adr/0001-cross-service-data-access-for-reporting.md) the chosen
  pattern is a sessions mirror — which needs a population/sync mechanism that
  does not yet exist.
- **Repayment:** scaffold the service (Alembic env + Postgres + CORS), add the
  mirror table and its sync, then the read endpoints.

### 4. Active-session guard is not race-proof — **Medium**
- **Location:** `quiz_session_route.py:114-117` (self-documented: "This
  check-then-act is not race-proof … needs a partial-unique constraint on
  (user_id, test_id) WHERE status='in_progress'").
- **Condition:** two near-simultaneous "start quiz" requests can both pass the
  existence check and both create sessions, letting a candidate re-roll the
  sampled question set.
- **Repayment:** a partial-unique index plus an Idempotency-Key on session
  creation (the same belt-and-suspenders the answer endpoint already uses).

### 5. Tests mock the DB session — **Medium**
- **Location:** `services/test-management-service/tests/test_quiz_session_route.py`
  uses a hand-rolled `_FakeSession`/`_AnswerSession` instead of a real engine.
- **Condition:** the fakes replay `execute`/`commit`/`rollback`, so real SQL
  errors, the `SELECT … FOR UPDATE` lock behavior, unique-constraint races, and
  migration drift are **not** exercised — a bug there ships with a green suite.
  This is deliberate (CI installs only `requirements.txt`, no async driver) but
  is a confidence gap.
- **Repayment:** the W3-F5 integration suite vs. real Postgres/Mongo (alembic
  upgrade fixture, pessimistic-lock concurrency test, idempotency test).

### 6. Answer-encoding coupling — **Medium**
- **Location:** `src/scoring/engine.py`, `AnswerSubmit` in
  `src/schemas/quiz_session_schema.py`. The engine compares correct/submitted as
  raw sets with no coercion.
- **Condition:** the contract is 1-indexed `option_id` ints. A frontend that
  submits 0-indexed indices or option text silently scores `0.0` on every
  multi-choice with no error. Now documented + regression-tested, but the
  coupling is real and will be exercised when the TestRunner submit path lands
  (W3-F4). See [ADR-0002](adr/0002-multi-select-scoring-algorithm.md).
- **Repayment:** integration test the real frontend→backend submit path.

### 7. Dead / stale code — **Medium**
- **Locations:**
  - `services/test-management-service/src/v1/routes/dashboard_route.py` — all
    handlers commented out, yet the gateway routes `/v1/api/dashboard/*` to this
    service (`services/api-gateway-service/main.py:44`) → those requests 404.
  - `services/api-gateway-service/main.py:262` `legacy_gateway` sits behind the
    catch-all `/{path:path}` (line ~158) and appears unreachable.
  - `frontend/src/lib/api/quiz-sessions.ts` — a two-part (Part A/B) adaptive-quiz
    client whose header and remaining `getPartAQuestions`/`submitPartA`/… helpers
    no longer match the single-session backend. The orphaned `createTestSession`
    was removed in W3-F3 (#151), but the rest of the Part A/B surface is still
    dead and should be deleted or rewritten to the single-session contract.
- **Condition:** misleads the next developer and leaves a routed-but-broken
  endpoint surface.
- **Repayment:** delete dead handlers / unreachable routes / stale client, or
  finish wiring them.

### 8. No essay/`text` auto-scoring — **Low**
- **Location:** `src/scoring/engine.py` (`text` falls through to exact-match;
  essay is a placeholder).
- **Condition:** any `text`/essay question cannot be auto-graded.
- **Repayment:** out of scope for the auto-scored quiz slice; needs a rubric or
  LLM-grader design before implementing.

### 9. Magic values not centralized — **Low**
- **Condition:** W4-F3 aggregate reporting needs a configurable "pass" threshold;
  pagination has a default page size. These should be config, not literals, once
  the reporting endpoints exist.
- **Repayment:** lift to `settings.py` when the aggregate endpoints are built.
