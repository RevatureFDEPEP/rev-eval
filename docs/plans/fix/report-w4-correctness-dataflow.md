# W4/W5 Correctness and Dataflow Fix Report

> Branch: `jor-w4-correctness-dataflow` (base `jorge-main`).
> Note: the execution prompt is internally inconsistent on the W4/W5 label;
> this report uses the branch name (`w4`). The work matches the W5
> correctness/dataflow issue list.

## Objective

Fix correctness/dataflow defects so submission summaries, dashboards,
reporting, question routing, gateway responses, and service startup behave
predictably instead of silently drifting or 500ing.

## Phase Summary

### Phase 1 — Test Management Dataflow, Scores, Config, and Ownership

#### Files Modified
- `services/test-management-service/src/services/quiz_session_service.py`
  - Reason: on final quiz submit, finalize the linked `TestSubmission`
    (`submitted_at`, `started_at` if missing, `ai_score`, `final_score`,
    status `COMPLETED`) in the same transaction; consistency-checked and
    idempotent.
- `services/test-management-service/src/models/test_submission.py`
  - Reason: `ai_score`/`trainer_score`/`final_score` `Integer` → `Float` to
    preserve fractional scores.
- `services/test-management-service/src/schemas/test_submission_schema.py`
  - Reason: score fields → `float`; `TrainerReviewRequest.trainer_score` is
    `float` bounded `0..100`.
- `services/test-management-service/src/services/test_submission_service.py`
  - Reason: enforce trainer ownership on evaluated and graded queues; guard
    optional `INTERVIEW_SERVICE_URL` (no `AttributeError`).
- `services/test-management-service/src/v1/routes/test_submission_route.py`
  - Reason: pass `trainer_id` to the now-ownership-scoped graded queue.
- `services/test-management-service/src/config/settings.py`
  - Reason: `USER_SERVICE_URL` default → `http://user-service:8002`; add
    optional `INTERVIEW_SERVICE_URL`.
- `services/test-management-service/src/v1/routes/dashboard_route.py` (removed)
  - Reason: dead commented-out stub, not wired into `main.py`.
- `services/test-management-service/migrations/001_float_scores.sql` (new)
  - Reason: ALTER existing score columns to double precision.
- `.env.example`, `docker-compose.yml`
  - Reason: document/wire optional `INTERVIEW_SERVICE_URL`.

#### What Went Well
- Finalization slots cleanly into `submit_session`; its existing replay guard
  makes it idempotent for free.
- Float migration is additive; SQLite test DB exercises fractional values.

#### What Failed and Was Fixed
- First INTERVIEW guard edit broke indentation under `else:`; rewritten to a
  proper nested block.
- New test used `from .conftest import` (relative) which pytest could not
  import; switched to `from conftest import` to match the repo convention.

#### Tests Run
- `tests/test_submission_finalize.py` (finalize, started_at preserve, mismatch
  reject, no-op, trainer-score bounds, evaluated-queue ownership).

#### Result
- Pass. Full test-mgmt suite: 63 passed.

### Phase 2 — Question Route Ordering

#### Files Modified
- `services/question-management-service/src/v1/routes/question_routes.py`
  - Reason: move dynamic `GET /{id}` after static GET routes so `/filter` and
    `/by-tags` are not shadowed.

#### What Went Well
- Pure reordering; no behavior change for valid ids.

#### What Failed and Was Fixed
- None.

#### Tests Run
- `tests/test_question_route_order.py` (filter + by-tags not shadowed, real id
  still reaches `get_by_id`).

#### Result
- Pass. Full question suite: 38 passed.

### Phase 3 — Gateway Empty-Body and Non-JSON Passthrough

#### Files Modified
- `services/api-gateway-service/main.py`
  - Reason: add `relay_downstream_response`; stop JSON-decoding 204/205/304 and
    empty bodies (which surfaced successful DELETEs as 500); relay non-JSON
    bodies unchanged. Applied to smart route and public auth proxy.

#### What Went Well
- Single shared helper covers both proxy paths.

#### What Failed and Was Fixed
- None.

#### Tests Run
- `tests/test_gateway_routing_and_auth.py` (relay 204/empty/non-JSON/JSON unit
  + DELETE 204 passthrough integration).

#### Result
- Pass. Gateway suite: 15 passed.

### Phase 4 — Startup Failure Hardening

#### Files Modified
- `services/test-management-service/src/db/session.py`
- `services/user-service/src/db/session.py`
  - Reason: `init_db` caught `OperationalError` and continued; now logs and
    re-raises so startup aborts and the container is reported unhealthy.

#### What Went Well
- Minimal, surgical re-raise.

#### What Failed and Was Fixed
- Ruff import-order on the new tests; autofixed.

#### Tests Run
- `tests/test_startup_failfast.py` in both services (init_db re-raises).

#### Result
- Pass. user-service: 17 passed.

## Final Validation

- Commands run:
  - `pytest` per service; `ruff check`; `docker compose config`.
- Passing tests: user 17, test-mgmt 63, question 38, gateway 15 (133 total).
- Failing tests: none.
- `docker compose config`: valid.
- Known follow-ups:
  - Existing DBs need `migrations/001_float_scores.sql` applied (create_all
    does not ALTER columns).
  - Admin cross-owner access to review queues is gated by an `ADMIN` role that
    does not yet exist in this branch's `UserRole`; ownership is enforced for
    trainers, admin bypass is a follow-up if/when the role lands.

## PR Notes

- Suggested PR title: `fix(correctness): submission dataflow, route order, gateway passthrough, startup`
- Summary: finalize quiz submissions into `TestSubmission`, preserve fractional
  scores, correct service URL defaults, optional interview integration, trainer
  review-queue ownership, question route ordering, gateway 204/empty/non-JSON
  passthrough, and fail-fast DB startup.
- Testing: `pytest` across the four services (133 passing), `ruff check`,
  `docker compose config`; manual gateway DELETE → 204 smoke recommended.
