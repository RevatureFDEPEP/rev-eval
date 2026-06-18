# Technical Debt Inventory

A structured walkthrough of the `rev-eval-f5` backend (the FastAPI microservices
under `services/`) conducted on **2026-06-18**. Each item records:

- **What** — the shortcut/debt.
- **Where** — file and line(s).
- **When it matters** — the condition under which the debt becomes a problem
  (it usually works fine at small scale).
- **Urgency** — `low` / `medium` / `high`, based on how close current/expected
  scale is to the breaking point.

> Scale assumptions for this POC: a Revature cohort is on the order of tens of
> trainers and low-thousands of participants; a participant accumulates dozens
> of attempts over a program. "Breaks at N" figures below are reasoned against
> that envelope.

---

## 1. Schema columns / tables created without a migration

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 1.1 | Core tables (`tests`, `skills`, `test_skills`, `test_submissions`) exist only as SQLAlchemy models and are created at runtime via `Base.metadata.create_all`, not via Alembic. The Alembic history (`001`, `002`) only covers `sessions`, `session_answers`, `idempotency_keys`. | [session.py:53-54](../services/test-management-service/src/db/session.py#L53-L54); models in [src/models/](../services/test-management-service/src/models/) | Fine on a fresh dev DB or SQLite. Breaks the first time a column on these tables changes against an existing Postgres volume: `create_all` is a no-op on existing tables, so the new column never appears and queries 500 in production. No controlled rollback path. | **high** |
| 1.2 | `engine = create_async_engine(..., echo=True)` ships SQL-echo logging on by default. | [session.py:25-29](../services/test-management-service/src/db/session.py#L25-L29) | Harmless in dev. At production request volume this floods logs and leaks query/parameter data into log storage. | medium |

**Recommendation:** generate a baseline Alembic migration for the four model-only
tables and switch startup to `alembic upgrade head` instead of `create_all`.

---

## 2. Endpoints that return all rows without pagination

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 2.1 | `GET /submissions/` → `list_all_submissions` → `TestSubmissionRepository.list_all` returns every submission row, unbounded. | [test_submission_route.py](../services/test-management-service/src/v1/routes/test_submission_route.py); [test_submission_service.py:160-162](../services/test-management-service/src/services/test_submission_service.py#L160-L162) | Fine at 50 submissions. At 5,000+ submissions the response is multi-MB and the trainer dashboard call times out. | **high** |
| 2.2 | `GET /submissions/trainer/all` and `/trainer/evaluated` load all matching submissions **and** issue one synchronous `httpx` call to user-service per row to resolve participant names (N+1 over the network). | [test_submission_service.py:399-429](../services/test-management-service/src/services/test_submission_service.py#L399-L429), [:299-332](../services/test-management-service/src/services/test_submission_service.py#L299-L332) | Fine at a handful of evaluated submissions. At a few hundred, the per-row HTTP fan-out makes the endpoint take seconds and couples it to user-service latency/availability. | **high** |
| 2.3 | `GET /tests/` → `TestService.list_all_tests` returns all tests unbounded. | [test_route.py](../services/test-management-service/src/v1/routes/test_route.py) | Tests grow slowly; fine for a long time. Becomes a problem only at thousands of tests. | low |
| 2.4 | `GET /skills/` returns all skills unbounded. | [skill_route.py](../services/test-management-service/src/v1/routes/skill_route.py) | Skills are a small, slow-growing reference set. Effectively never breaks. | low |
| 2.5 | `GET /questions/` returns all questions from MongoDB unbounded. | [question_routes.py:60-70](../services/question-management-service/src/v1/routes/question_routes.py#L60-L70) | Fine for a small question bank. A bank in the thousands makes this a heavy, slow scan with no caps. | medium |

**Note — already done right:** the reporting service's attempts endpoint
(`GET /reports/user/{id}/attempts`) is properly paginated/filtered/sorted with
bounded page size (`size` capped at 100). See
[report_repository.py:79-101](../services/reporting-and-analytics-service/src/repositories/report_repository.py#L79-L101). User-service `GET /users/`
also paginates (limit 1–1000). These are the template the endpoints above
should follow.

---

## 3. Missing / weak input validation

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 3.1 | `trainer_score` (and `ai_score`, `final_score`) typed as plain `int` with no bounds, despite the documented "0–100" contract. A trainer review can persist `-5` or `9999`. | [test_submission_schema.py:43-45](../services/test-management-service/src/schemas/test_submission_schema.py#L43-L45); model [test_submission.py](../services/test-management-service/src/models/test_submission.py) | Out-of-range scores corrupt averages/best-score aggregates in reporting and any pass/fail logic. Matters as soon as one bad value is entered. | **high** |
| 3.2 | No DB `CHECK` constraint backing the score range, so even a fixed schema can't be the last line of defense. | [test_submission.py:33-35](../services/test-management-service/src/models/test_submission.py#L33-L35) | Same blast radius as 3.1; defense-in-depth gap. | medium |
| 3.3 | `user_id` path/query params accepted as bare `int` with no `ge=1` floor (e.g. submissions filter, report endpoints). | [test_submission_route.py](../services/test-management-service/src/v1/routes/test_submission_route.py); [report_route.py:19](../services/reporting-and-analytics-service/src/v1/routes/report_route.py#L19) | Negative/zero IDs just return empty results rather than a 422 — confusing, not catastrophic. | low |
| 3.4 | Direct repository `limit` defaults (`limit: int = 100`) on question-management have no upper clamp; a future caller can request an arbitrarily large page. | [question_repository.py:35](../services/question-management-service/src/repositories/question_repository.py#L35) and siblings | Only matters if an internal caller passes a huge limit; the HTTP layer doesn't yet expose it. | low |

---

## 4. Hardcoded magic values

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 4.1 | `JWT_SECRET = "change-me-in-production"` default in settings. | [user-service settings.py:20](../services/user-service/src/config/settings.py#L20) | A deploy that forgets to set the env var ships a publicly-known signing secret → full auth bypass. CI does inject a secret, but the insecure default still exists in code. | **high** |
| 4.2 | `timeout=30.0` hardcoded across ~8 outbound `httpx` calls; `_DEFAULT_DURATION_SECONDS = 7200`; question-count fallback `or 20`; user-service-URL/question-service-URL string defaults. | [test_submission_service.py](../services/test-management-service/src/services/test_submission_service.py) (×5), [session_service.py:30-34,63](../services/test-management-service/src/services/session_service.py#L30-L34), [api-gateway main.py](../services/api-gateway-service/main.py) (×3) | Works fine; the cost is operability — tuning timeouts/durations means a code change and redeploy instead of config. | medium |
| 4.3 | `JWT_EXPIRY_MINUTES = 60`, `S3_PRESIGN_EXPIRY_SECONDS = 3600`, `MONGO_TIMEOUT_MS = 5000` baked as defaults. | [user-service settings.py:22](../services/user-service/src/config/settings.py#L22), [question-management settings.py:31,41](../services/question-management-service/src/config/settings.py#L31) | These are at least centralized in settings; acceptable. Listed for completeness. | low |
| 4.4 | Seed/dev password `password123` and hardcoded seed scores in `seed_db.py`. | [seed_db.py:18](../services/test-management-service/seed_db.py#L18) | Dev-only script; risk only if ever run against a shared/staging DB. | low |

---

## 5. Commented-out code & inline TODOs

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 5.1 | ~100-line commented-out service-to-service block (user lookup + SQS event publishing) left inside `create_submission`. | [test_submission_service.py:29-133](../services/test-management-service/src/services/test_submission_service.py#L29-L133) | Pure noise that obscures the 3-line live path and rots as the surrounding code moves. The real logic now lives in `bulk_assign_test`. | medium |
| 5.2 | ~260 lines of commented-out dashboard endpoints. | [dashboard_route.py:34-296](../services/test-management-service/src/v1/routes/dashboard_route.py#L34-L296) | Dead weight; the canonical version is git history, not comments. | medium |
| 5.3 | `# Remove timezone for POC - TODO: fix with timezone-aware DB` — timestamps are force-stripped to naive UTC. | [test_submission_schema.py:30](../services/test-management-service/src/schemas/test_submission_schema.py#L30); also `session_service.py` uses `datetime.utcnow()` | Fine while everything is one region/naive. Breaks correctness once clients in multiple timezones submit, or when comparing naive vs aware datetimes (raises `TypeError`). | medium |
| 5.4 | `datetime.utcnow()` (deprecated in 3.12) used for all server-authoritative timing in sessions. | [session_service.py:111,179](../services/test-management-service/src/services/session_service.py#L111) | Works now; emits deprecation warnings and will break on a future Python. | low |

---

## 6. Tests: mocks where integration would give more confidence

The backend test suites are, on the whole, **integration-first** — they run
against a real in-memory SQLite engine rather than mocking the repository layer,
which is the right call. The gaps are about *coverage of the cross-service
seams*, not over-mocking.

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 6.1 | `SessionService.submit_answer` is exercised at the unit level (scoring) and via smoke tests, but the live `httpx` calls to question-management-service are not covered by an integration test against a stubbed-or-real question service. The scoring branch selection (exact vs partial) is only validated through the pure scorers. | [test_scoring.py](../services/test-management-service/tests/test_scoring.py), [test_session_smoke.py](../services/test-management-service/tests/test_session_smoke.py) | A change to the question-service response shape (`type` vs `question_type`, `correct_answers` vs `answers`) would pass all tests but break scoring in production. | medium |
| 6.2 | The reporting `session_mirror` is **seeded directly in tests** because the projection writer from test-management does not exist yet (see ADR 0002 follow-up). So there is no test that an attempt completed in test-management actually shows up in reporting. | [reporting conftest.py](../services/reporting-and-analytics-service/tests/conftest.py) | Entirely correct given the projection is unbuilt — but it means the end-to-end "finish quiz → see it in your report" path is untested. Becomes important the moment the projection writer lands. | medium |
| 6.3 | The per-row user-service name-resolution fan-out (items 2.2) has no test asserting graceful degradation when user-service returns non-200 / times out beyond the inline `try/except`. | [test_submission_service.py:307-328](../services/test-management-service/src/services/test_submission_service.py#L307-L328) | The fallback (`User #<id>`) is plausible but unverified; a regression there would silently mislabel every participant. | low |

---

## 7. Correctness debt found during the walkthrough

| # | What | Where | When it matters | Urgency |
|---|------|-------|-----------------|---------|
| 7.1 | In `submit_answer`, `await db.commit()` is only called **inside** the `if idempotency_key:` block. When a client submits an answer without an `Idempotency-Key` header, the answer/scoring write and index advance rely on the `get_db` context manager committing — but `get_db` does **not** commit, it only closes. So an answer submitted without the header may not be durably persisted. | [session_service.py:293-304](../services/test-management-service/src/services/session_service.py#L293-L304), [session.py:39-41](../services/test-management-service/src/db/session.py#L39-L41) | Works in tests that always pass a key (or where the in-memory session is reused). In production, answers submitted without the optional header can be lost on connection close. | **high** |

> 7.1 is the one item here that is a latent bug rather than scaling debt. It is
> documented but intentionally **not** fixed in this PR, which is scoped to the
> debt inventory and ADRs; it is filed here so the fix is tracked and reviewed
> on its own.

---

## Urgency rollup

- **High:** 1.1 (no migrations), 2.1/2.2 (unbounded + N+1 submission lists),
  3.1 (unbounded score), 4.1 (default JWT secret), 7.1 (commit path).
- **Medium:** 1.2, 2.5, 3.2, 4.2, 5.1, 5.2, 5.3, 6.1, 6.2.
- **Low:** 2.3, 2.4, 3.3, 3.4, 4.3, 4.4, 5.4, 6.3.
</content>
</invoke>
