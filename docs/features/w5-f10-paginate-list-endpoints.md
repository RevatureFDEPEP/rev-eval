# W5-F10 — Paginate the return-all-rows list endpoints

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin:
[technical-debt.md](../technical-debt.md) §2; **repayment backlog item 4**.
**Depends on:** W5-F8 (central pagination config) preferred first; W4-F1 already
models the target envelope.
**Unblocks:** bounded payloads/latency as tables grow past demo scale.
**Last updated:** 2026-06-17

## Problem

Several list endpoints return all rows — fine on seeded demo data, O(n) payload +
DB scan as the table fills. The W4 reporting endpoints
(`/reports/user/{id}/attempts`) already model the intended `{items,total,page,size}`
envelope; these predate it:

```
services/test-management-service/src/v1/routes/test_route.py         GET /tests/, /tests/created-by/{uid}, /tests/submissions-by/{uid}
services/test-management-service/.../routes/category_route.py        GET /categories/, /categories/{id}/skills
services/test-management-service/.../routes/skill_route.py           GET /skills/
services/test-management-service/.../routes/test_submission_route.py GET /submissions/ + 4 trainer/graded variants
services/question-management-service/.../routes/question_routes.py    GET /questions/ (get_all_questions)
```

## Steps

- [ ] **1. Adopt the W4 envelope** — add `page`/`size` query params (defaults/caps
      from W5-F8 config) and return `{items,total,page,size}` on the endpoints above.
      Mirror `AttemptsQuery` (W4-F1) for consistency.
- [ ] **2. Repository support** — push LIMIT/OFFSET + a count query into the repo
      layer; avoid loading all rows to slice in Python.
- [ ] **3. Frontend callers** — update any client/server caller that assumes a bare
      array so it reads `items` (and can page). No UX regression on existing screens.
- [ ] **4. Tests** — per endpoint: default page, explicit page/size, `total`
      correctness, out-of-range page → empty `items`. Repo-level LIMIT/OFFSET unit test.

## Out of scope

- Cursor/keyset pagination — offset envelope matching W4 is sufficient at this scale.
- The central config extraction itself (that is W5-F8).

## Acceptance

- [ ] Listed endpoints return the paginated envelope; large tables no longer return
      all rows; existing callers still work.
- [ ] Tests green; `FEATURE_STATUS.md` row ✅; debt §2 / repayment 4 cross-referenced.
