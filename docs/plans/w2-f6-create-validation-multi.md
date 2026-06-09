# W2-F6 — Structured Question Authoring: close the create-time validation gap (Hybrid)

## Context

W2-F6 (`docs/features/w2-f6-question-authoring-ui.md`) is 🟡 In Progress. The
question-authoring form, dynamic per-type fields, Zod validation, and
gateway-POST submit are all done. The one open item the doc flags is **create-time
options validation**.

Investigation surfaced *why* it's open: the create flow is built around
**auto-promotion**. The question-list "Create Question" menu only offers `mcq`,
`true_false`, and `text` — there is **no entry point for multi-select**. Authoring
a multi-select question today means clicking "Create MCQ", checking 2+ correct
boxes, and letting `transformFormData` silently promote `mcq → multi` at submit
(`question-form-utils.ts:202-208`). So "enforce MCQ exactly-one at create" can't
be a simple schema swap — it would delete the only path to multi-select questions.

**Decision (user): Hybrid.** Make multi-select a **first-class** create type with
its own strict schema, while **keeping** the mcq auto-promote convenience. Net
effect: multi authoring no longer depends on a side-effect; mcq stays lenient
(exactly-one is intentionally *not* enforced at create — promotion is the design).

## Approach

All changes are frontend-only, under `frontend/`.

### 1. Add a strict create-multi schema — `src/components/trainer/question-form-utils.ts`

- Add `createMultiSchema`: same shape as `editMultiSchema` (`:101-116`) — 2-5
  options, `correctCount >= 1 && correctCount < options.length` ("at least one,
  but not all"). Reuse that refine body/message.
- Wire it in `buildQuestionSchema` (`:130-148`): the `case "multi"` create branch
  currently falls back to `createOptionsSchema` (`:140`) — point it at
  `createMultiSchema`. Leave `case "mcq"` create → `createOptionsSchema` (lenient,
  `:136`) unchanged.

### 2. Stop create-multi from down-promoting to mcq — same file, `transformFormData`

- The create branch (`:202-208`) sets `actualType = "mcq"` whenever exactly one
  box is checked. For a question authored *as* multi that's wrong. Guard the
  promotion so it only applies when `questionType === "mcq"`; when
  `questionType === "multi"`, keep `actualType = "multi"` regardless of count.
- `getDefaultValues` already handles `"multi"` identically to `"mcq"` (`:160-169`)
  — no change.

### 3. Add the "Multi-Select" create entry — `src/app/(dashboard)/trainer/questions/page.tsx`

- Two `DropdownMenu`s push `?type=...`: the header menu (`:277-294`) and the
  empty-state menu (`:365-379`). Add a `multi` item to **both**, after the MCQ
  item, e.g. `router.push("/trainer/questions/create?type=multi")` with label
  "Multi-Select" / "Multiple choice with several correct answers".
- The create page already passes `searchParams.get("type")` straight through
  (`create/page.tsx:15`), so `?type=multi` flows to the form with no page change.

### 4. Mode/type-aware options helper text — `src/components/trainer/QuestionForm.tsx`

- The `CardDescription` (`:305-311`) branches on edit-mcq / edit-multi / else.
  Add a **create-multi** branch so the form tells the author "at least one, but
  not all" instead of the lenient "one or multiple" copy. Confirm `isOptionsType`
  already covers `"multi"` (it drives this whole card); if it's mcq-only, widen it
  to include `"multi"`.

### 5. Tests — `src/components/trainer/__tests__/`

- `question-schemas.test.ts`: add a `buildQuestionSchema("create","multi")`
  describe block — accept ≥1-not-all, reject zero-correct, reject all-correct,
  reject <2/>5 options. Mirror the existing edit-multi block (`:159-186`).
- `question-form-utils.test.ts`: add a `transformFormData` create-multi case
  asserting type **stays** `"multi"` even with a single correct option (the
  no-down-promote fix). Keep the existing mcq promotion tests (`:109`, `:226`)
  — that behavior is intentionally retained.

### 6. Docs (same PR, per the tracker workflow)

- `docs/features/w2-f6-question-authoring-ui.md`: flip Status → ✅ Completed.
  Rewrite step 3 / Remaining: multi-select is now a first-class create type with
  strict validation; record that mcq exactly-one is **intentionally not** enforced
  at create because mcq→multi auto-promotion is the chosen design (note the
  divergence from alexis #59's `superRefine` approach).
- `docs/FEATURE_STATUS.md`: W2-F6 row 🟡 → ✅.

## Branch & commit cadence

- Branch off `richardh` → `richardh-feat-w2f6`.
- Commit after each major milestone:
  1. schema + transform fix (steps 1-2) + their tests (step 5),
  2. UI wiring — dropdown entries + helper text (steps 3-4),
  3. docs (step 6: W2-F6 detail + FEATURE_STATUS).
- Run `pnpm test` + `pnpm lint` green before the docs commit.

## Out of scope

- mcq create-time "exactly one" enforcement (deliberately kept lenient).
- Backend changes — multi with ≥1 correct is already valid server-side.
- File-upload field (belongs to W2-F5).

## Verification

1. `cd frontend && pnpm test` — new create-multi schema + transform tests pass,
   existing promotion tests still green.
2. `pnpm lint` clean.
3. Manual (`docker compose up`, log in as a trainer):
   - `/trainer/questions` → "Create Question" now lists **Multi-Select**.
   - Create-multi: all-correct or zero-correct → inline Zod error; ≥1-not-all →
     submits; verify the stored question is `type: "multi"` even with one correct
     box checked (the no-promote fix) via the question list / Mongo.
   - Create-mcq unchanged: one correct → mcq; 2+ correct → still promotes to multi.
