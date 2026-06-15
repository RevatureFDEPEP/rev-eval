# AI Assistance — Disclosure & Verbal Defence

**Last updated:** 2026-06-15 (W4-F5, Day 20)

## Disclosure

The W2–W4 feature work in this repository was developed with **AI assistance
(Claude Code)** under human review. Each feature followed the same loop: a
written plan (`docs/plans/`) approved before any code, milestone-scoped commits,
tests run with real output, and a requirements review against the feature spec
before merge. The AI drafted code and docs; the human (Richard Hawkins) reviewed,
corrected, and made the final architectural calls — recorded in the feature
detail docs, the ADRs, and the commit history.

## Annotation convention

Annotating *every* AI-touched line would be noise — the whole codebase qualifies.
Instead, the most **consequential** AI-drafted sections carry a one-line inline
marker pointing here:

```
AI-assisted (Claude Code); human-reviewed <area> — see docs/ai-assistance.md.
```

Annotated sections (the two ADR subjects + the two narrative features' core
seams):

| Section | File | Decision it embodies |
|---|---|---|
| Multi-select scoring (Jaccard) | `services/test-management-service/src/scoring/partial_credit.py` | ADR 0002 |
| Reporting cross-service read engine | `services/reporting-and-analytics-service/src/db/session.py` (`tms_engine`/`get_tms_db`) | ADR 0001 |
| `require_trainer` JWT re-verify | `services/reporting-and-analytics-service/src/v1/dependencies/auth.py` | W4-F3 defense-in-depth |
| `resolveAccess` RBAC resolver | `frontend/src/lib/auth/access.ts` | W4-F4 server-side gate |

## Verbal defence (per annotated section)

### 1. Multi-select scoring — `partial_credit.py`
- **What the AI produced:** a `score_question` returning the Jaccard index of
  correct vs. submitted option sets, plus the alternatives write-up.
- **What changed in review:** the algorithm choice was made *by the human* —
  the AI drafted all three candidates (all-or-nothing, correct-minus-wrong,
  Jaccard) and the symmetry argument was the deciding factor I accepted. The
  empty-correct-set guard (`return 0.0`) and the `is_correct = score == 1.0`
  convention were tightened to match the state machine's needs.
- **Why this shape:** symmetry penalizes missed-correct and spurious-wrong
  equally, so "select everything" can't game the score; bounded `[0,1]` averages
  cleanly for the W4 reports. Full rationale in ADR 0002.

### 2. Reporting cross-service read engine — `db/session.py`
- **What the AI produced:** a second read-only async engine (`tms_engine`) over
  test-management's Postgres, with `get_tms_db()` and a startup connectivity
  check for both DBs.
- **What changed in review:** the *pattern* (shared-DB direct read vs. HTTP vs.
  event projection) was the human decision, captured in ADR 0001. The
  containment rules — TMS tables on their own `TmsBase`, never in reporting's
  Alembic `target_metadata`, SELECT-only — were added so the coupling is
  bounded and a TMS schema change fails loudly in CI.
- **Why this shape:** zero sync lag and single-round-trip SQL aggregates at
  local scale; the repository layer is the documented seam for swapping in a
  projection later.

### 3. `require_trainer` — `auth.py`
- **What the AI produced:** a FastAPI dependency decoding the Bearer JWT with
  python-jose and the shared secret, 401 on missing/invalid/expired, 403 on a
  non-TRAINER verified role.
- **What changed in review:** the deliberate decision to make reporting the one
  service that re-verifies the JWT (rather than trusting `X-User-*` headers like
  the others) is the human call — defense-in-depth for trainer-level data.
  Spec-strict role handling (ADMIN excluded, role read only from the verified
  payload) was confirmed against W4-F3 and exercised with spoofed-header curls.
- **Why this shape:** the gateway is the platform auth boundary, but
  trainer-level aggregate data warrants an independent gate so a direct hit to
  `:8004` with forged headers is still rejected.

### 4. `resolveAccess` — `access.ts`
- **What the AI produced:** a pure prefix→roles resolver shared by the Edge
  middleware and the per-page `getSession` re-check, with no `next/server`
  imports so it unit-tests under vitest.
- **What changed in review:** the `/admin` = TRAINER-only mapping (ADMIN
  redirected, not 403-walled) was aligned by hand to the W4-F3 backend gate so
  the frontend and backend agree; the "UX affordance ≠ security gate" boundary
  was made explicit in the comments.
- **Why this shape:** one pure function as the single source of truth for both
  enforcement points avoids the two gates drifting apart.
