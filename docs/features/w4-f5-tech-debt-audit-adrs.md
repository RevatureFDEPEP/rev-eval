# W4-F5 — Technical Debt Audit & ADR Documentation

**Status:** ❌ Not Started
**Spec:** `days_16_20_features.md` §5 (Day 20)
**Depends on:** [W4-F1](w4-f1-results-reporting-endpoints.md) (the cross-service data-access decision is one required ADR), [W3-F2](w3-f2-scoring-engine-locking.md) (the partial-credit scoring algorithm choice is the second required ADR), plus a substantially complete codebase (all prior features at least partially implemented)
**Unblocks:** — (capstone; reflective deliverable)
**Last updated:** 2026-06-08

Identify, document, and rank the technical shortcuts taken across the four
weeks; write ADRs for the two or three most consequential choices; produce a
prioritized repayment backlog.

## Steps

- [ ] **1. Structured walkthrough** — inventory shortcuts: inline TODOs, missing
      input validation, hardcoded magic values, unpaginated all-rows endpoints,
      mocks where integration tests would give more confidence, schema columns
      added without a migration. *(This repo's [W2-F8](w2-f8-pre-existing-defects.md)
      defect log is a starting seed.)*
- [ ] **2. Debt inventory** — `docs/technical-debt.md`. Per item: name, code
      location, the condition under which it matters (e.g. "fine at 50 users,
      breaks at 5,000"), and urgency (low/med/high vs. current scale).
- [ ] **3. ADRs** — `docs/adr/`, standard structure (context / decision /
      consequences / alternatives). **Required two:** (a) cross-service
      data-access pattern for reporting (shared DB vs. API call vs. event
      projection — from W4-F1); (b) multi-select scoring algorithm (full-match
      vs. Jaccard vs. set-overlap — from W3-F2).
- [ ] **4. AI-assistance annotations** — for AI-drafted sections, add an inline
      comment noting AI involvement + the human review that followed; prepare a
      short verbal defence (what AI produced, what changed, why).
- [ ] **5. Technical narrative** — one-page what/why/how for the two most
      interesting features, each tied to a concrete decision and its ADR.

## Notes

- Two ADRs are pre-determined by the spec (W4-F1 data access, W3-F2 scoring) —
  capture those decisions *as they are made* in the respective features rather
  than reconstructing them on Day 20.
- The existing `docs/FEATURE_STATUS.md` + `docs/features/` tracker is itself
  evidence for the narrative (what/why/how is already partly recorded per
  feature).

## Remaining

All steps.
