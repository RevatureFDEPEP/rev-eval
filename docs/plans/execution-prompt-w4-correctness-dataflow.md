# Claude Execution Prompt — W5 Correctness and Dataflow Fixes

## Target Branch

`jor-w4-correctness-dataflow`

## Source Plan

Use this plan as the starting point:

`docs/plans/execution-prompt-w4-correctness-dataflow.md`

Do not blindly apply the plan. First inspect the current repo, validate each issue, and adjust only when the code has changed.

---

## Mission

Validate and implement correctness/dataflow fixes for Week 5.

Issues to validate:

* Quiz final submit does not update linked `TestSubmission`.
* Fractional scores may be truncated.
* `INTERVIEW_SERVICE_URL` may be missing or undefined.
* `USER_SERVICE_URL` may default to the wrong port.
* Trainer evaluated/review queues may ignore ownership.
* `dashboard_route.py` may be only a commented-out stub.
* Question static routes such as `/filter` and `/by-tags` may be shadowed by dynamic ID routes.
* Startup may swallow DB, seed, or migration failures.
* API gateway may convert downstream `204 No Content`, empty bodies, or non-JSON bodies into `500`.

If plan needs modification, update this document.

---

## Permission Model

Before coding:

1. Inspect the repo.
2. Confirm working tree is clean.
3. Validate the current phase against the repo.
4. Report each issue as:

   * confirmed
   * partially confirmed
   * already fixed
   * not found
5. Propose the first implementation slice.
6. Ask permission to create the branch and begin Phase 1.

After permission is granted for a phase, work independently within that approved phase.

Do not stop after every small edit.

Ask for permission again only if:

* the approved phase plan must change
* files outside the approved phase scope must be changed
* testing reveals issues that require a second round of changes beyond normal in-scope fixes
* a critical design, security, data-loss, migration, deployment, or breaking-change decision is required
* repo state conflicts with the approved plan

During an approved phase, you may:

* create or update files required for that phase
* refactor code needed to complete the phase cleanly
* add or update tests
* run tests, linters, formatters, and validation commands
* fix normal implementation issues found during testing
* continue until the phase is implemented and tested

---

## Pre-Coding Commands

```bash
cd d:/_Revature/rev-eval
git status --short
git branch --show-current
git log --oneline --decorate -5
```

If the working tree is not clean, stop and report the changed files.

After approval:

```bash
git switch jorge-main
git pull --ff-only origin jorge-main
git switch -c jor-w4-correctness-dataflow
git status
```

If `jorge-main` is not the correct base branch, stop and report before creating the branch.

---

## Required Validation Report Before Coding

```md
## Correctness/dataflow validation report

### Confirmed
- Issue:
  - Evidence:
  - Impact:
  - Proposed fix:
  - Files likely changed:

### Partially confirmed / needs adjustment
- Issue:
  - What differs from the plan:
  - Revised safer approach:

### Already fixed / not found
- Issue:
  - Evidence:
  - Code change needed? yes/no

### Recommended first implementation slice
1. ...
2. ...
3. ...

May I create branch `jor-w4-correctness-dataflow` and begin Phase 1?
```

---

# Implementation Plan

## Phase 1 — Test Management Dataflow, Scores, Config, and Ownership

### Objective

Fix test-management-service correctness issues affecting quiz submission summaries, score precision, service URLs, trainer review ownership, and dashboard routing.

### Validate and Fix

1. Final quiz submit updates the linked `TestSubmission`.
2. `TestSubmission` receives:

   * `submitted_at`
   * `started_at` if missing
   * `final_score`
   * `ai_score` when the quiz auto-score is the system/AI score
   * completed/submitted status using the existing enum
3. Final submit is idempotent.
4. Linked submission consistency is enforced:

   * submission user matches session user
   * submission test matches session test
5. Score persistence supports decimal values.
6. Schemas expose score fields as floats, not integers.
7. Missing `INTERVIEW_SERVICE_URL` returns controlled behavior, not `AttributeError`.
8. `USER_SERVICE_URL` defaults to user-service port `8002`.
9. Trainer evaluated/review queues enforce test ownership.
10. Dashboard stub is removed or clearly marked deprecated if dashboard data now comes from reporting/submission APIs.

### Likely Files

* `services/test-management-service/src/services/quiz_session_service.py`
* `services/test-management-service/src/services/test_submission_service.py`
* `services/test-management-service/src/repositories/test_submission_repository.py`
* `services/test-management-service/src/models/test_submission.py`
* `services/test-management-service/src/schemas/test_submission_schema.py`
* `services/test-management-service/src/config/settings.py`
* `services/test-management-service/src/v1/routes/dashboard_route.py`
* `services/test-management-service/main.py`
* `.env.example`
* `docker-compose.yml`

### Code Comment Rules

Add brief comments only where future maintainers could misunderstand the reason:

* `TestSubmission` is the durable dashboard/reporting summary.
* Fractional scores must not be truncated.
* Missing interview integration must be handled intentionally.
* Trainer ownership prevents cross-trainer review queue leakage.

### Tests

Cover:

* final submit updates linked submission
* repeated submit does not corrupt score or timestamps
* mismatched session/submission user or test is rejected
* fractional score persists and returns unchanged
* trainer score validation still enforces `0 <= score <= 100`
* missing interview URL does not raise `AttributeError`
* non-interview submissions do not call interview service
* trainer A cannot see or review trainer B submissions
* admin behavior remains explicit

---

## Phase 2 — Question Route Ordering

### Objective

Ensure static question routes are registered before dynamic ID routes.

### Validate and Fix

Move static routes above `/{id}` or equivalent dynamic routes:

* `/filter`
* `/by-tags`
* `/by-type/{question_type}`
* `/by-skill/{skill}`
* `/by-difficulty/{difficulty}`

Add clean invalid-ID handling if practical.

### Likely Files

* `services/question-management-service/src/v1/routes/question_routes.py`
* related question route tests

### Code Comment Rule

Add a short comment only if needed explaining that static routes must be registered before dynamic ID routes to avoid shadowing.

### Tests

Cover:

* `/v1/api/questions/filter`
* `/v1/api/questions/by-tags`
* invalid ID behavior

---

## Phase 3 — Gateway Empty-Body and Non-JSON Passthrough

### Objective

Make the API gateway faithfully relay downstream empty-body and non-JSON responses.

### Validate and Fix

1. Do not call `resp.json()` for:

   * `204`
   * `205`
   * `304`
   * empty response bodies
2. Preserve original downstream status codes.
3. Relay non-JSON response bodies unchanged with content type.
4. Apply the same handling anywhere the gateway marshals downstream responses, including auth proxy paths if present.

### Likely Files

* `services/api-gateway-service/main.py`
* gateway tests if present

### Code Comment Rule

Add a short comment explaining that empty successful responses must not be JSON-decoded because decoding an empty body masks success as `500`.

### Tests

Cover:

* downstream `204` returns gateway `204`
* empty body does not become `500`
* non-JSON body is relayed unchanged
* normal JSON responses still work

---

## Phase 4 — Startup Failure Hardening

### Objective

Fail fast when DB initialization, migration, or seed startup fails.

### Validate and Fix

1. Find startup/init DB code.
2. If DB init catches `OperationalError` or seed/migration errors, log and re-raise.
3. Ensure container/service health reflects startup failure instead of allowing later runtime `500`s.

### Likely Files

* `services/test-management-service/main.py`
* `services/test-management-service/src/db/session.py`
* `services/user-service/src/db/session.py`
* startup scripts or seed modules, if present

### Code Comment Rule

Add a short comment explaining that startup should fail fast because an unhealthy service is easier to diagnose than hidden runtime DB failures.

### Tests

Cover:

* DB init failure raises
* startup does not swallow migration/seed failures

---

## Phase 5 — Documentation, Report, and PR Prep

### Objective

Document what changed, how it was tested, what went well, and what failed and was fixed.

### Required Report

Create this file:

`docs/plans/fix/report-w4-correctness-dataflow.md`

Use this structure:

```md
# W5 Correctness and Dataflow Fix Report

## Objectiveyes

Briefly explain the goal of this fix branch.

## Phase Summary

### Phase 1 — Test Management Dataflow, Scores, Config, and Ownership

#### Files Modified
- `path/to/file`
  - Reason:

#### What Went Well
-

#### What Failed and Was Fixed
-

#### Tests Run
-

#### Result
-

### Phase 2 — Question Route Ordering

#### Files Modified
- `path/to/file`
  - Reason:

#### What Went Well
-

#### What Failed and Was Fixed
-

#### Tests Run
-

#### Result
-

### Phase 3 — Gateway Empty-Body and Non-JSON Passthrough

#### Files Modified
- `path/to/file`
  - Reason:

#### What Went Well
-

#### What Failed and Was Fixed
-

#### Tests Run
-

#### Result
-

### Phase 4 — Startup Failure Hardening

#### Files Modified
- `path/to/file`
  - Reason:

#### What Went Well
-

#### What Failed and Was Fixed
-

#### Tests Run
-

#### Result
-

## Final Validation

- Commands run:
- Passing tests:
- Failing tests, if any:
- Known follow-ups:

## PR Notes

- Suggested PR title:
- Summary:
- Testing:
```

### Documentation Updates

Update only documentation affected by actual code changes:

* `docs/plans/fix/report-w5-correctness-dataflow.md`
* affected README files
* `.env.example` if environment variables changed
* compose docs if service URLs or ports changed
* testing notes if verification commands changed

---

# Acceptance Criteria

* Quiz final submit updates linked `TestSubmission`.
* Dashboards/reports can read correct score, status, and submission timestamp.
* Fractional scores are preserved.
* Question static routes are not shadowed by dynamic ID routes.
* Missing `INTERVIEW_SERVICE_URL` produces controlled behavior.
* `USER_SERVICE_URL` defaults to the real user-service port.
* Trainer ownership is enforced in evaluated/review queues.
* Dashboard stub is removed or clearly deprecated.
* Startup fails loudly on DB/seed/migration initialization failure.
* Gateway relays `204`, empty bodies, and non-JSON bodies correctly.
* Tests cover the fixed behavior.
* `docs/plans/fix/report-w5-correctness-dataflow.md` is created.

---

# Verification Commands

Run what applies based on changed files:

```bash
pytest services/test-management-service/tests
pytest services/question-management-service/tests
pytest services/api-gateway-service/tests
docker compose config
```

Targeted checks if files exist:

```bash
pytest services/test-management-service/tests/test_quiz_session.py
pytest services/test-management-service/tests/test_scoring.py
pytest services/test-management-service/tests/test_services_and_repositories.py
pytest services/question-management-service/tests
```

Manual smoke checks if services are running:

```bash
curl -i -X POST http://localhost:8000/v1/api/sessions/<session_id>/submit -H "Authorization: Bearer <participant-token>"
curl -i http://localhost:8000/v1/api/submissions/<submission_id> -H "Authorization: Bearer <participant-token>"
curl -i "http://localhost:8000/v1/api/questions/filter?type=mcq" -H "Authorization: Bearer <trainer-token>"
curl -i "http://localhost:8000/v1/api/questions/by-tags?tags=java" -H "Authorization: Bearer <trainer-token>"
curl -i -X DELETE http://localhost:8000/v1/api/submissions/<submission_id>/ -H "Authorization: Bearer <trainer-or-admin-token>"
```

Gateway DELETE must return `204`, not `500`.

---

# Commit and PR Rules

Do not include:

* `Generated by Claude`
* `Authored by Claude`
* `Co-authored-by: Claude`
* `Created with Claude`
* `Claude Code`

Use normal project-style commits.

Suggested commit groups:

```bash
git add services/test-management-service .env.example docker-compose.yml
git commit -m "fix(submissions): correct quiz submission dataflow"

git add services/question-management-service
git commit -m "fix(questions): prevent static route shadowing"

git add services/api-gateway-service
git commit -m "fix(gateway): relay empty downstream responses"

git add services/user-service services/test-management-service
git commit -m "fix(startup): fail fast on database initialization errors"

git add docs README.md .env.example docker-compose.yml
git commit -m "docs(correctness): record dataflow validation"
```

Adjust commits based on actual changed files.

Before PR:

```bash
git status
git diff --stat origin/jorge-main...HEAD
git log --oneline origin/jorge-main..HEAD
```

Prepare a PR title and markdown body for manual submission.

Do not create the PR unless explicitly asked.
