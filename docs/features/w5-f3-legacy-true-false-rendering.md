# W5-F3 — Render legacy option-less `true_false` questions

**Status:** ✅ Completed (2026-06-18)
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

- [x] **1. Pick the approach** — chose **(a)** dedicated `TrueFalseQuestion` widget
      in `components/take/` (no data writes, lowest blast radius). Plan:
      [docs/plans/w5-f3-legacy-true-false-rendering.md](../plans/w5-f3-legacy-true-false-rendering.md).
- [x] **2. Implement** —
      `frontend/src/components/take/TrueFalseQuestion.tsx` renders True/False as a
      RadioGroup (a11y parity: `labelledBy`/`disabled`), encoding True→`[1]` /
      False→`[0]` to keep the uniform `number[]` answer shape. `TestRunner.tsx`
      dispatch routes option-less `true_false` to it; a `true_false` *with*
      options still uses `SingleSelectQuestion`. **Scores with no backend change:**
      server scoring is exact set-equality (`scoring/exact_match.py`) and Python
      `True==1`/`False==0`, so `{1}=={true}` and `{0}=={false}` against the stored
      `correct_answers: [bool]`. (Finding: option-less is the *canonical* shape,
      not legacy — `trainer/question-form-utils.ts:223-226`.)
- [x] **3. Frontend tests** — `take/TrueFalseQuestion.test.tsx` (render no-error,
      True→`[1]`, False→`[0]`, selection reflection, disabled blocks) +
      `take/TestRunner.test.tsx` dispatch case (option-less true_false → no error,
      submits `[1]`). mcq/multi suites unchanged. 163 tests pass.
- [x] **4. Optional** — approach (a) used (no normalization). Flagged the seed
      data defect (`seed_rag_context_questions.py:48`, `correct_answers:[0]` but
      "True") in technical-debt.md §7 for a separate data fix; bank not mutated.

## Out of scope

- A full Mongo question-shape migration framework (debt §4) — handled separately.

## Acceptance

- [x] A legacy option-less `true_false` doc renders a working True/False control,
      not "No options available". (`take/TrueFalseQuestion.tsx`; dispatch
      `take/TestRunner.tsx`.)
- [x] Frontend tests green (163 passed); `pnpm lint` (0 errors) / `pnpm build`
      clean.
- [x] `FEATURE_STATUS.md` row flipped to ✅; debt §7 cross-referenced as closed.
