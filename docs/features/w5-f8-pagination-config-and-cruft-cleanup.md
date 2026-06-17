# W5-F8 — Central pagination config + dead-code / cruft cleanup

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: in-source TODO/cruft;
catalogued in [technical-debt.md](../technical-debt.md) §1 (line 32), §8 (lines 90-91),
and the dead aspirational invite/notification blocks found during the deferral sweep.
**Depends on:** none.
**Unblocks:** consistent pagination limits; a cleaner, less-misleading tree.
**Last updated:** 2026-06-17

This is a low-risk maintainability batch — two loosely related cleanup tracks that
do not each warrant their own feature. Each track ends with its own commit.

## Steps

### Track A — central pagination config

- [ ] **1. Single source for page-size defaults/caps** — replace the scattered
      `100`/`500`/`20`/`1000` magic numbers with a shared config (settings or a
      constants module) per service. Sites:
      `services/test-management-service/.../routes/...`,
      `services/question-management-service/.../routes/question_routes.py`,
      `services/user-service/src/v1/routes/user_route.py:49`.
- [ ] **2. Apply** the shared defaults at the existing list endpoints without
      changing their response contract (this is config extraction, not the §2
      "paginate the unpaginated endpoints" work — that is separate).

### Track B — dead code & cruft

- [ ] **3. Remove the commented-out invite/notification blocks** (dead aspirational
      code) in
      `services/test-management-service/src/services/test_submission_service.py`
      (around lines 54-72, 221) — they reference services that do not exist.
- [ ] **4. Cruft** — git-ignore/remove the checked-in
      `services/test-management-service/dev.db` (debt §8); either delete or clearly
      mark the stale `start.sh` / `test-services.sh` as non-authoritative (debt §8
      lines 90-91). Confirm `docker-compose.yml` remains the single source of truth.

### Both

- [ ] **5. Tests/CI** — existing suites stay green (no behavior change intended);
      lint/build clean. Note any removed file in the commit body.

## Out of scope

- Actually paginating the return-all-rows endpoints (debt §2) — that is a separate
  feature using the W4 `page/size/total` envelope.
- Security defaults (`JWT_SECRET`, CORS) — high-urgency, tracked in the
  [technical-debt.md](../technical-debt.md) repayment backlog, not bundled here.

## Acceptance

- [ ] Page-size limits come from one config per service; no scattered magic numbers
      at the listed sites.
- [ ] Dead commented blocks removed; `dev.db` git-ignored/removed; stale scripts
      handled.
- [ ] Suites + lint/build green; `FEATURE_STATUS.md` row flipped to ✅.
