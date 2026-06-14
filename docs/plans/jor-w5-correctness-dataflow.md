# Week 5 Correctness and Dataflow Plan

**Branch:** `jor-w5-correctness-dataflow`
**Date:** 2026-06-13
**Source of record:** `D:\_Revature\Week4\ClaudePrompt.txt` + repo scan from a full-stack/FDE perspective

---

## 1. Executive summary

This plan addresses the correctness/dataflow issues called out for `jor-w5-correctness-dataflow`.

**Reason to fix:** quiz completion, trainer dashboards, reporting, and interview review depend on consistent submission state. Today, the quiz session stores its aggregate score on `quiz_sessions`, but the linked `test_submissions` row is not finalized, so dashboards and reporting can show stale or missing results. Several adjacent bugs make that worse: route ordering can hide filter endpoints, undefined service URLs can turn review endpoints into 500s, score columns truncate fractional results, and startup can continue after database init failure.

**Fix strategy:** make `TestSubmission` the durable cross-service summary of participant progress, preserve `QuizSession` as the detailed attempt record, and tighten route/config/startup behavior so the platform fails predictably instead of silently drifting.

---

## 2. Confirmed repo findings

| Finding from prompt | Repo evidence | Impact | Proposed fix |
|---|---|---|---|
| Quiz score not propagated to `TestSubmission` | `QuizSessionService.submit_session` computes `total_score`, `max_score`, `percentage_score`, `submitted_at`, and session status, but never updates the linked submission. | Participant dashboard, trainer dashboard, reporting service, and submission list APIs read stale `final_score/status/submitted_at`. | On final submit, update the linked `TestSubmission` in the same transaction: `final_score`, `ai_score` if appropriate, `status`, `submitted_at`, and `started_at` if missing. |
| `INTERVIEW_SERVICE_URL` undefined | `TestSubmissionService.get_submission_review_details` and `submit_trainer_review` read `settings.INTERVIEW_SERVICE_URL`, but `Settings` defines only `USER_SERVICE_URL` and `QUESTION_SERVICE_URL`. | Interview review routes can raise `AttributeError` and return 500 before making an upstream call. | Add `INTERVIEW_SERVICE_URL` to settings and compose, or make interview-service integration optional with a graceful 503/nullable transcript path. |
| Question `/filter` and `/by-tags` route-ordering shadow | `question_routes.py` registers `/{id}` before `/by-tags` and `/filter`. | `/questions/filter` and `/questions/by-tags` can be treated as Mongo IDs, causing wrong 404/500 behavior. | Move all static filter routes before `/{id}`, or constrain `/{id}` to Mongo ObjectId format. |
| `dashboard_route.py` commented-out stub | `dashboard_route.py` contains only commented endpoints and is not included in `test-management-service/main.py`. Frontend dashboard routes appear to rely on newer APIs instead. | Dead code misleads development and may hide missing product contracts. | Either remove the stub or replace it with tested live dashboard endpoints wired through `main.py`. |
| `USER_SERVICE_URL` wrong port default | `services/test-management-service/src/config/settings.py` defaults `USER_SERVICE_URL` to `http://localhost:8003`; compose correctly sets `http://user-service:8002`. | Local/non-compose runs call question-service port instead of user-service; participant name lookup and auth header resolution break. | Change default to `http://user-service:8002` or require env var. Keep test override support. |
| Integer score-column truncation | `TestSubmission.ai_score`, `trainer_score`, and `final_score` are `Integer`; quiz/session scoring uses floats for partial credit. | Multi-select partial credit and percentages can be truncated, corrupting analytics and grades. | Convert score columns/schemas to `Float`/`Numeric`, with a migration or documented recreate path for dev DB. |
| `get_evaluated_submissions` ignores trainer ownership | Service comment explicitly says any trainer can review any interview; query does not filter by `Test.created_by_id == trainer_id`. | Correctness and security issue: trainer queues contain submissions for other trainers. | Filter by owning trainer, with admin-only cross-owner view if needed. |
| Boot swallows seed/migration failures | User-service and test-management `init_db` catch `OperationalError`, print, and do not re-raise. | Containers can report healthy enough to keep running while tables/DB are unavailable, producing later runtime failures. | Re-raise startup DB init failures and let healthchecks/restart policy surface the problem. |

---

## 3. Development plan

### Phase 1 - Finalize submission state when quiz is submitted

1. Extend `services/test-management-service/src/repositories/test_submission_repository.py`:
   - add a row-locking fetch helper for submission finalization, for example `get_by_id_for_update`
   - add a focused update helper for quiz completion fields
2. Update `services/test-management-service/src/services/quiz_session_service.py`:
   - when `session.submission_id` exists, fetch the submission under the same transaction used to finalize the session
   - verify `submission.user_id == session.user_id` and `submission.test_id == session.test_id`
   - set:
     - `submitted_at = now`
     - `started_at = session.server_started_at` if unset
     - `final_score = percentage`
     - `ai_score = percentage` for auto-scored quizzes, unless product wants `final_score` only
     - `status = COMPLETED` for normal submit, or `ABANDONED`/existing expired equivalent if the session timed out
   - make idempotent re-submit return existing values without double writes
3. Decide status semantics:
   - recommended: `COMPLETED` means quiz submitted and auto-scored; `EVALUATED` remains interview AI-evaluated pending trainer review; `GRADED` means trainer final review
4. Add tests in `services/test-management-service/tests/test_quiz_session.py` or a new focused file:
   - final submit updates linked `TestSubmission`
   - idempotent final submit does not change timestamps/scores unexpectedly
   - mismatched `submission_id`/user/test is rejected
   - expired submit status behavior is explicit

**Defended choice:** propagate to `TestSubmission` during final submit instead of relying on async reconciliation. This system already uses synchronous APIs and dashboards read `test_submissions`; updating there at the source of finalization is simpler, deterministic, and easier to test.

### Phase 2 - Preserve fractional scores end to end

1. Change model fields in `services/test-management-service/src/models/test_submission.py`:
   - `ai_score`, `trainer_score`, `final_score` from `Integer` to `Float` or `Numeric(5, 2)`
2. Change schemas in `services/test-management-service/src/schemas/test_submission_schema.py`:
   - score fields from `Optional[int]` to `Optional[float]`
   - trainer review validation should enforce `0 <= score <= 100`
3. Update analytics and frontend expectations if they currently assume integers:
   - round only at display boundaries
   - keep API payloads numeric floats
4. Add migration path:
   - if no Alembic exists, document a dev DB recreate or add a simple SQL migration script under docs/ops
5. Tests:
   - partial-credit score like `66.67` persists and returns unchanged
   - trainer review accepts decimal where product allows it, or explicitly rounds once if decimals are rejected

**Defended choice:** use decimal-capable storage because the quiz scoring engine already produces non-integer values. Rounding in the database would permanently lose information and make analytics inconsistent.

### Phase 3 - Fix route ordering for question filters

1. Move these static routes above `@router.get("/{id}")`, `PUT /{id}`, and `DELETE /{id}`:
   - `/by-type/{question_type}`
   - `/by-skill/{skill}`
   - `/by-difficulty/{difficulty}`
   - `/by-tags`
   - `/filter`
2. Prefer an additional guard:
   - rename ID route parameter to `question_id`
   - validate it with an ObjectId-compatible type/pattern
3. Add tests in `services/question-management-service/tests/`:
   - `GET /v1/api/questions/filter?...` calls filter service logic
   - `GET /v1/api/questions/by-tags?...` calls tag logic
   - invalid IDs return a clean 422/404 without shadowing static paths

**Defended choice:** static-before-dynamic is the least surprising FastAPI pattern. An ObjectId constraint is extra protection, but moving routes is the immediate fix.

### Phase 4 - Service URL settings and interview integration behavior

1. Update `services/test-management-service/src/config/settings.py`:
   - fix `USER_SERVICE_URL` default to `http://user-service:8002`
   - add `INTERVIEW_SERVICE_URL: Optional[str] = None` or a real default if the service exists in compose
2. Update `docker-compose.yml`:
   - add `INTERVIEW_SERVICE_URL` only if an interview service is present or expected
   - otherwise leave it unset and make the app handle missing integration gracefully
3. Update `TestSubmissionService.get_submission_review_details`:
   - if no interview URL is configured and the test type is interview, return transcript as `None` plus a clear metadata warning, or return `503` if transcript is mandatory
4. Update `submit_trainer_review`:
   - avoid touching interview service when URL is unset or when test type is not `INTERVIEW`
   - if saving trainer evaluation is required, surface a controlled 503 rather than silently swallowing permanent config errors
5. Tests:
   - missing `INTERVIEW_SERVICE_URL` does not produce an `AttributeError`
   - configured URL is called for interview submissions
   - non-interview submissions never call interview service

**Defended choice:** optional integration behavior should be explicit. Returning a controlled unavailable state is better than broad exception swallowing because frontend and QA can distinguish "no transcript service" from "submission not found."

### Phase 5 - Trainer ownership in evaluated/graded queues

1. Update `TestSubmissionService.get_evaluated_submissions_for_trainer`:
   - filter by `Test.created_by_id == trainer_id`
   - retain admin-all behavior only through a separate admin dependency/endpoint
2. Audit related routes:
   - `get_graded_submissions`
   - `get_submission_review_details`
   - `submit_trainer_review`
3. Add shared ownership helper to avoid repeating query logic.
4. Tests:
   - trainer A sees only trainer A pending/evaluated submissions
   - trainer A cannot fetch review details for trainer B submission
   - admin can see cross-owner data if product requires it

**Defended choice:** even though this overlaps security, it also fixes product correctness. Trainers should not see queues they cannot act on, and dashboards should not mix ownership boundaries.

### Phase 6 - Dashboard stub decision

1. Pick one of two paths:
   - remove `services/test-management-service/src/v1/routes/dashboard_route.py` if dashboard data now comes from reporting and submission/test routes
   - or implement live dashboard routes and include the router in `main.py`
2. Recommended path:
   - remove/comment-prune the stale stub from runtime planning
   - keep dashboard aggregation in `reporting-and-analytics-service` and frontend BFF endpoints
3. If implementing live endpoints:
   - wire `dashboard_route.router` into `main.py`
   - use current async SQLAlchemy models
   - enforce role and ownership
   - add tests

**Defended choice:** deleting the dead stub is preferable if reporting owns analytics. Keeping two dashboard sources increases drift and makes future defects harder to diagnose.

### Phase 7 - Startup failure behavior

1. Update `services/user-service/src/db/session.py` and `services/test-management-service/src/db/session.py`:
   - after logging `OperationalError`, re-raise
   - consider catching broader SQLAlchemy init exceptions and re-raising after structured logging
2. Ensure startup hooks fail the container when DB init fails.
3. Review `start.sh` scripts:
   - if a script catches init errors, it should `exit 1`
4. Tests:
   - monkeypatch engine connect/create to raise and assert startup/init raises
   - optionally test container health behavior via `docker compose up` smoke

**Defended choice:** fail-fast startup is less forgiving in the moment, but it prevents a half-initialized service from accepting traffic and producing confusing downstream 500s.

---

## 4. Acceptance criteria

- Submitting a quiz updates both `quiz_sessions` and the linked `test_submissions` summary fields.
- Dashboards and submission APIs show the submitted quiz's status, score, and timestamp without a background reconciliation step.
- Fractional scores survive database, schema, API, and frontend display paths.
- `/v1/api/questions/filter` and `/v1/api/questions/by-tags` hit their intended handlers.
- Missing `INTERVIEW_SERVICE_URL` never raises `AttributeError`; behavior is explicit and tested.
- Test-management defaults point to `user-service:8002`, not question-service.
- Evaluated/review queues are trainer-owned unless the caller is admin.
- Service startup fails loudly when DB initialization fails.

---

## 5. Suggested verification commands

```powershell
pytest services/test-management-service/tests/test_quiz_session.py
pytest services/test-management-service/tests/test_scoring.py
pytest services/test-management-service/tests/test_services_and_repositories.py
pytest services/question-management-service/tests
docker compose config
```

Manual smoke checks:

```powershell
# Submit a quiz session, then verify the linked submission row reports final_score/status/submitted_at.
curl -i -X POST http://localhost:8000/v1/api/sessions/<session_id>/submit -H "Authorization: Bearer <participant-token>"
curl -i http://localhost:8000/v1/api/submissions/<submission_id>/ -H "Authorization: Bearer <participant-token>"

# Verify static question filter routes are not swallowed as IDs.
curl -i "http://localhost:8000/v1/api/questions/filter?type=mcq" -H "Authorization: Bearer <trainer-token>"
curl -i "http://localhost:8000/v1/api/questions/by-tags?tags=java" -H "Authorization: Bearer <trainer-token>"
```

---

## 6. Out of scope

- Rebuilding the dashboard UI. This branch should make data correct and APIs reliable; visual redesign belongs elsewhere.
- Adding a full migration framework if project scope only allows a dev DB recreate. The plan still calls out the schema change so data correctness is explicit.
- Replacing the quiz scoring algorithms. The issue here is propagation/storage, not scoring logic itself.
