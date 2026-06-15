# W4-F5 — Technical Debt Audit & ADR Documentation

**Status:** ✅ Completed
**Spec:** `days_16_20_features.md` §5 (Day 20)
**Depends on:** [W4-F1](w4-f1-results-reporting-endpoints.md) (the cross-service data-access decision is one required ADR), [W3-F2](w3-f2-scoring-engine-locking.md) (the partial-credit scoring algorithm choice is the second required ADR), plus a substantially complete codebase (all prior features at least partially implemented)
**Unblocks:** — (capstone; reflective deliverable)
**Last updated:** 2026-06-08

Identify, document, and rank the technical shortcuts taken across the four
weeks; write ADRs for the two or three most consequential choices; produce a
prioritized repayment backlog.

## Steps

- [x] **1. Structured walkthrough** — inventory shortcuts: inline TODOs, missing
      input validation, hardcoded magic values, unpaginated all-rows endpoints,
      mocks where integration tests would give more confidence, schema columns
      added without a migration. *(This repo's [W2-F8](w2-f8-pre-existing-defects.md)
      defect log is a starting seed.)* — done via a thorough codebase sweep;
      findings grouped in `docs/technical-debt.md` §1–§8 (high-urgency claims
      file:line-verified: `JWT_SECRET` default, CORS `*`, MinIO creds, TODO,
      true_false render).
- [x] **2. Debt inventory** — `docs/technical-debt.md`. Per item: name, code
      location, the condition under which it matters (e.g. "fine at 50 users,
      breaks at 5,000"), and urgency (low/med/high vs. current scale). — 8
      categories in tables + a prioritized repayment backlog; commit `32077d6`.
- [x] **3. ADRs** — `docs/adr/`, standard structure (context / decision /
      consequences / alternatives). **Required two:** (a) cross-service
      data-access pattern for reporting (shared DB vs. API call vs. event
      projection — from W4-F1); (b) multi-select scoring algorithm (full-match
      vs. Jaccard vs. set-overlap — from W3-F2). — (a) `docs/adr/0001-...md`
      already written during W4-F1; (b) `docs/adr/0002-multiselect-scoring-algorithm.md`
      added, commit `4aef373`.
- [x] **4. AI-assistance annotations** — for AI-drafted sections, add an inline
      comment noting AI involvement + the human review that followed; prepare a
      short verbal defence (what AI produced, what changed, why). — `docs/ai-assistance.md`
      (disclosure + convention + per-section verbal defence) plus comment-only
      annotations on the 4 most consequential seams (`partial_credit.py`,
      reporting `db/session.py`, `auth.py`, `access.ts`); commit `d1ff8a1`.
      Scope deliberately bounded to representative sections — whole repo is
      AI-assisted, so the convention is documented rather than applied to every
      file (recorded in `docs/ai-assistance.md`).
- [x] **5. Technical narrative** — one-page what/why/how for the two most
      interesting features, each tied to a concrete decision and its ADR. —
      `docs/technical-narrative.md`: reporting cross-service access (→ ADR 0001)
      + scoring engine & locking (→ ADR 0002); commit `f84dc41`.

## Evidence

- Debt inventory: `docs/technical-debt.md` — commit `32077d6`.
- ADR 0002 (scoring): `docs/adr/0002-multiselect-scoring-algorithm.md` — commit
  `4aef373`; ADR 0001 (data access) pre-existing from W4-F1.
- AI-assistance: `docs/ai-assistance.md` + comment-only annotations in
  `services/test-management-service/src/scoring/partial_credit.py`,
  `services/reporting-and-analytics-service/src/db/session.py`,
  `services/reporting-and-analytics-service/src/v1/dependencies/auth.py`,
  `frontend/src/lib/auth/access.ts` — commit `d1ff8a1`.
- Technical narrative: `docs/technical-narrative.md` — commit `f84dc41`.
- Plan: `docs/plans/w4-f5-tech-debt-audit-adrs.md` — commit `9337271`.
- Validation: code diff is comment-only/all-additive (10 insertions, 0
  deletions across 4 files); `pnpm lint` 0 errors, `pnpm build` clean; added
  Python comment lines ≤85 chars (< ruff 88 default; ruff not installed locally
  but no behaviour or import change).

## Notes

- Two ADRs are pre-determined by the spec (W4-F1 data access, W3-F2 scoring) —
  capture those decisions *as they are made* in the respective features rather
  than reconstructing them on Day 20.
- **Debt-inventory seed from W3-F6:** legacy option-less `true_false`
  question docs (pre-W2-F6 shape, `correct_answers: [true]`, no `options`
  array) render as "No options available" in the `/take` TestRunner — the
  legacy quiz page had a dedicated True/False widget; `/take` routes the type
  to the options-based single-select (see
  [w3-f6 Notes](w3-f6-playwright-e2e-smoke.md)). Fix is a bank data
  migration/normalization or a true_false widget in
  `frontend/src/components/take/`. Urgency: low — only stale local dev
  volumes hold such docs; CI and fresh stacks never see them.
- The existing `docs/FEATURE_STATUS.md` + `docs/features/` tracker is itself
  evidence for the narrative (what/why/how is already partly recorded per
  feature).

## Remaining

None — all 5 steps complete. The debt items inventoried here are *catalogued,
not repaid*: the prioritized repayment backlog in `docs/technical-debt.md` is
the to-do list for future features (none owned by W4-F5).
