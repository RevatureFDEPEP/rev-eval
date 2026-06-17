# W5-F3 — Render legacy option-less `true_false` questions

**Status:** ❌ Not Started
**Spec:** trainer-defined remediation (non-catalog). Origin: surfaced by
[W3-F6](w3-f6-playwright-e2e-smoke.md) E2E, recorded as cleanup candidate;
catalogued in [technical-debt.md](../technical-debt.md) §7 (line 83).
**Depends on:** none.
**Unblocks:** legacy/seeded `true_false` docs render instead of erroring.
**Last updated:** 2026-06-17

## Problem

Pre-W2-F6 `true_false` question docs carry `correct_answers: [true]` with **no
`options` array**. The take-page routes them to the options-based single-select
widget, which renders "Error: No options available":

```
frontend/src/components/take/SingleSelectQuestion.tsx:30-31
frontend/src/components/quiz/MultiQuestion.tsx:22
frontend/src/components/quiz/MCQQuestion.tsx:22
```

Per debt §7 this only bites **stale local dev volumes** — CI and fresh stacks seed
the current shape — so urgency is low, but it is a real broken render when it hits.
Two fix paths (pick one): a dedicated true/false widget that synthesizes
True/False options, or a bank data-normalization that backfills `options`.

## Steps

- [ ] **1. Pick the approach** — (a) dedicated `TrueFalseQuestion` widget in
      `components/take/` that renders True/False when `options` is absent and maps
      the choice to the boolean answer shape, or (b) a normalization that injects
      canonical options for option-less `true_false` docs at read time. (a) is the
      lower-blast-radius default (no data writes).
- [ ] **2. Implement** the chosen path; ensure both legacy (`[true]`, no options)
      and current (`options` present) shapes render and score correctly.
- [ ] **3. Frontend tests** — render a legacy option-less `true_false` doc → no
      error, selectable True/False; current-shape doc still renders unchanged.
- [ ] **4. Optional** — if normalization (b), a one-off/idempotent backfill note
      for the Mongo bank; do not silently mutate without a documented migration.

## Out of scope

- A full Mongo question-shape migration framework (debt §4) — handled separately.

## Acceptance

- [ ] A legacy option-less `true_false` doc renders a working True/False control,
      not "No options available".
- [ ] Frontend tests green; `pnpm lint`/`build` clean.
- [ ] `FEATURE_STATUS.md` row flipped to ✅; debt §7 cross-referenced as closed.
