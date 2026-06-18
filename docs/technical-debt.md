# Technical debt inventory

A structured walkthrough of shortcuts taken across the platform, captured at the
end of W4. Each item lists where it lives, the condition under which it starts to
matter, and an urgency. "Accepted" means a deliberate, documented trade-off, not
an oversight. Line numbers are point-in-time (branch `armaan/w4-f5-tech-debt-adrs`)
— treat them as anchors, not guarantees.

| # | Debt | Location | Why it matters / when it bites | Urgency |
|---|------|----------|-------------------------------|---------|
| 1 | **No integration tests** — unit suites mock the DB with aiosqlite; no real Postgres/Mongo fixtures, no pessimistic-lock or idempotency concurrency test, no CI service-containers. | `services/*/conftest.py` (sqlite only); no `pytest.mark.integration`/testcontainers anywhere. W3-F5 not started. | SQLite ignores `with_for_update()`, so the answer-endpoint lock + cross-user idempotency are exercised only by hand (live round-trips), never in CI. A regression in the lock/finalize path ships green. | High |
| 2 | **user-service has no migrations** — schema created by `Base.metadata.create_all` on startup, no Alembic. | `services/user-service/src/db/session.py:35`. test-management moved to Alembic in W2-F7; user-service did not. | `create_all` never ALTERs an existing table. Any column change to `users` silently no-ops on an existing volume → drift between code and DB, only caught by a fresh volume. | Medium |
| 3 | **Unpaginated list endpoints** — full-table reads with no limit/offset. | `question-management-service/src/services/question_service.py:74` (`get_all_questions`); `test-management-service/src/services/test_submission_service.py:366` (`get_all_submissions_for_trainer`). | Fine at seed scale (tens of rows). Once the question bank or submission history grows, these load the whole table into memory per request. Reporting endpoints (W4-F1) are paginated; these predate that discipline. | Medium |
| 4 | **MinIO orphan objects** — presigned upload mints an object key before the question doc is created; abandon the form and the object is never referenced or cleaned up. | `question-management-service/src/services/upload_service.py` (no cleanup path). Accepted in W2-F5. | Storage slowly leaks unreferenced blobs. No correctness impact. Bites only if upload abandonment is frequent or storage is metered. Needs a sweep/GC job or upload-on-submit. | Low (accepted) |
| 5 | **Reporting summary total ≠ attempts-list total** — summary aggregates count SUBMITTED only; the attempts list returns all statuses. | `reporting-and-analytics-service/src/services/reports_service.py` (SUBMITTED-filtered aggregates vs unfiltered list). | By design (avg/best/time only make sense over completed attempts), but a consumer that diffs the two totals will see a mismatch. Documented here so it reads as intent, not a bug. | Low (accepted) |
| 6 | **TEXT questions are not auto-scorable** — scoring raises `ValueError`; the answer endpoint catches it and records a `manual_grading_required` zero so the session advances. | `test-management-service/src/scoring/exact_match.py:37`; handler in `session_service.submit_answer`. See [ADR 0002](adr/0002-multi-select-scoring-algorithm.md). | A TEXT question in a test scores 0 for every candidate until a manual-grading surface exists. No such surface is built. Avoid TEXT in scored tests, or build grading. | Medium |
| 7 | **No ADMIN account seeded** — the ADMIN role exists and is enforced, but `seed_db.py` creates only TRAINER/PARTICIPANT; register defaults to PARTICIPANT. | `test-management-service/seed_db.py` (no ADMIN insert). | Any admin-gated surface can't be exercised without a manual DB insert. Testing/demo friction, not a runtime fault. | Low |
| 8 | **Reporting read-only models duplicate test-management's schema** — a minimal column subset is re-declared on `TmsBase`; a rename/drop upstream is not caught at compile time. | `reporting-and-analytics-service/src/models/tms_readonly.py`. Accepted in [ADR 0001](adr/0001-reporting-cross-service-data-access.md). | Schema coupling: a column rename in test-management breaks reporting at query time, not at build. Mitigation (integration tests, item 1) is itself unbuilt — so this compounds with #1. | Medium |
| 9 | **Answer-key exposure is gate-, not schema-, enforced** — answer-bearing question reads are locked behind `require_trainer`; internal scoring calls pass a trusted `X-User-Role: TRAINER` on gateway-bypassing direct calls. | `question-management-service` read routes; `test-management-service` `_fetch_question`. Hardened in W3-F1 follow-up. | Correct today because the gateway overwrites `X-User-Role` from the verified JWT, so a browser can't forge trainer. But the safety depends on that invariant holding — if any direct path skips the gateway without re-checking, the key leaks. Worth a defense-in-depth schema split (public vs full) everywhere, not just `/sample`. | Medium |
| 10 | **Pydantic class-based `Config`** — models use the deprecated `class Config` style; two harmless pytest warnings (Config + `Test` model collection). | e.g. `question-management-service/src/models/question.py:98`; consistent across services. | Cosmetic now. Becomes real work at the Pydantic v2 `ConfigDict` migration, and the warnings mask any genuinely new warning in CI logs. | Low |

## Walkthrough method

Scanned for the standard shortcut signatures: TODO/FIXME/HACK markers (none
found — debt here is structural, not flagged), `create_all` vs Alembic per
service, list endpoints without `limit`, mocks standing in for integration
coverage, schema columns added outside a migration, and magic literals (the
session-duration fallback is a *named* constant `_DEFAULT_DURATION`, not a magic
value — not debt). Items rejected after verification: the once-suspected
`GET /skills/{id}` 500 — `skill_service.get_by_id` exists and the route is wired
(`skill_route.py:19`), so there is no latent crash.
