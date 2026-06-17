# W5-F7 — Per-question drill-down on the trainer dashboard

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: backend endpoint
shipped in [W4-F3](w4-f3-rbac-aggregate-queries.md) but never consumed by the
frontend; flagged as a candidate follow-up in
[W4-F4 plan](../plans/w4-f4-trainer-dashboard-frontend.md) lines 208,211.
**Depends on:** W4-F3 (`GET /reports/test/{id}/questions`), W4-F4 (dashboard).
**Unblocks:** trainers see per-question difficulty, not just per-test aggregates.
**Last updated:** 2026-06-17

## Problem

W4-F3 added `GET /reports/test/{id}/questions` — per-question correct-rate, a
hardest-first `RANK()`, and a 4-bucket partial-credit histogram — but the W4-F4
trainer dashboard only renders per-test aggregates and the timeseries. The
endpoint exists and is `require_trainer`-gated; nothing on the frontend calls it,
so the per-question insight is invisible.

## Steps

- [ ] **1. Server-side fetch** — add a server-side client call for
      `/reports/test/{id}/questions` (mirror the W4-F2/W4-F4 `getUserReport*Server`
      pattern, forwarding the `auth_token` JWT).
- [ ] **2. Drill-down surface** — when a test is selected on `/admin/dashboard`,
      render a per-question region: hardest-first list/table with correct-rate and
      the partial-credit histogram. Reuse `<ChartWrapper>` (W4-F2 reuse surface).
- [ ] **3. Loading + error isolation** — own `loading.tsx` skeleton +
      `SectionErrorFallback`, matching the W4-F4 per-panel isolation so a failing
      call blanks only this region.
- [ ] **4. RBAC parity** — TRAINER-only, consistent with the existing `/admin`
      server-side gate; no new client-trust.
- [ ] **5. Tests** — transform/render of the questions payload; empty-state; 403/empty
      handling. `pnpm lint`/`build` clean.

## Out of scope

- New backend reporting endpoints — consume the existing W4-F3 one as-is.

## Acceptance

- [ ] Selecting a test shows per-question correct-rate + histogram, hardest-first.
- [ ] Panel isolates its own loading/error state; TRAINER-only.
- [ ] Frontend tests + lint/build green; `FEATURE_STATUS.md` row flipped to ✅.
