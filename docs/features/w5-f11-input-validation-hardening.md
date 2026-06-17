# W5-F11 — Input validation hardening (filter enums + presign content-type)

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin:
[technical-debt.md](../technical-debt.md) §3; **repayment backlog item 7**.
**Depends on:** question-management-service.
**Unblocks:** 422-on-bad-input instead of silent empty results / unenforced types.
**Last updated:** 2026-06-17

## Problem

- **Raw-string filter params, no enum** (med) — `by-type`, `by-skill`,
  `by-difficulty`, `filter` reach the query layer unvalidated; a typo returns empty
  rather than 422, and the accepted surface is wider than the documented value set.
  `services/question-management-service/src/v1/routes/question_routes.py`.
- **Presigned `content_type` not enforced** (low) — docstring says
  `image/png`/`image/jpeg` but nothing rejects other types at the boundary.
  `question_routes.py` (`/questions/presigned-upload-url`).

## Steps

- [ ] **1. Enum the filter params** — replace raw `str` path/query params with
      `Enum`/`Literal` types (or validated values) for `by-type`, `by-difficulty`,
      and any closed-set `filter`; out-of-set input → 422. `by-skill` validated
      against known skills where feasible.
- [ ] **2. Enforce presign content-type** — reject content types outside the allowed
      image set in the `/questions/presigned-upload-url` handler (not just the
      docstring); 422 on disallowed type.
- [ ] **3. Tests** — bad enum value → 422; valid value → 200; disallowed presign
      content-type → 422; allowed → signed URL.
- [ ] **4. Docs** — narrow the route docstrings to the enforced value set.

## Out of scope

- Re-validating already-typed/constrained params elsewhere — these two sites only.

## Acceptance

- [ ] Out-of-set filter values and disallowed presign content-types return 422.
- [ ] Tests green; `FEATURE_STATUS.md` row ✅; debt §3 / repayment 7 cross-referenced.
