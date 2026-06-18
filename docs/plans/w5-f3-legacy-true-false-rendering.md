# W5-F3 — Render legacy option-less `true_false` questions — Plan

**Feature:** W5-F3 — Render legacy option-less `true_false` questions
**Detail doc:** [docs/features/w5-f3-legacy-true-false-rendering.md](../features/w5-f3-legacy-true-false-rendering.md)
**Spec origin:** trainer-defined remediation; technical-debt.md §7 (line 83), surfaced by W3-F6 E2E.
**Depends on:** none.
**Unblocks:** legacy/seeded `true_false` docs render and score instead of erroring.

## Locked decision

- **Approach (a): dedicated `TrueFalseQuestion` widget in `frontend/src/components/take/`.**
  No data writes / no Mongo backfill (lowest blast radius, per detail doc step 1).

## Context — what we found (read before reviewing)

The detail doc and debt §7 frame this as a *legacy-only* problem ("only stale
local dev volumes"). **That framing is inaccurate and the plan corrects it:**

- The W2-F6 authoring UI builds every `true_false` question as
  `correct_answers = [boolean]`, `options = undefined`
  (`frontend/src/components/trainer/question-form-utils.ts:223-226`). So
  **option-less is the *canonical* current shape for `true_false`, not just a
  legacy artifact.** Freshly authored and seeded true/false questions all lack
  `options`.
- The take flow dispatches `mcq` + `true_false` to the options-based
  `SingleSelectQuestion`, which renders **"Error: No options available"** for any
  option-less doc (`frontend/src/components/take/SingleSelectQuestion.tsx:30-31`,
  dispatch at `TestRunner.tsx:65-87`). → **All true/false questions are
  currently unanswerable in the take flow.**

### Answer-shape & scoring constraints (these drive the design)

- The take flow keeps a **uniform `Map<string, number[]>`** answer shape — every
  leaf widget emits a list of `option_id` numbers; autosave / submit / scoring
  all assume this (`TestRunner.tsx:106`, `performSubmit` at `:118-150`).
- Server scoring for `true_false` is **exact set-equality** between
  `correct_answers` and the submitted list
  (`services/test-management-service/src/scoring/exact_match.py:12-28`, dispatched
  from `scoring/__init__.py`). Questions are scored server-side from the stored
  doc (`session_service.py:265-283`); the sanitizer passes `options` through
  untouched (`session_service.py:60-70`).
- **Python set-equality bridges bool↔int:** `True == 1`, `False == 0`, so
  `{True} == {1}` and `{False} == {0}`. Therefore a widget that submits **`[1]`
  for True and `[0]` for False** scores correctly against the canonical
  `correct_answers: [true]` / `[false]` **with zero backend changes.**

### Known dirty seed data (documented, not silently fixed)

`services/question-management-service/seed_rag_context_questions.py` has
inconsistent true/false encodings: one doc uses `correct_answers: [0]` while its
explanation says **"True"** (line 48), conflicting with the boolean convention
where `0 == False`. No single client mapping can score a self-contradictory doc.
This is a **seed data defect**, not a render bug. A full question-shape migration
is **out of scope** (debt §4 / detail doc "Out of scope"). The plan **flags** it
(milestone 4) and leaves a one-line note rather than mutating the bank.

## Files this touches

- **new** `frontend/src/components/take/TrueFalseQuestion.tsx` — widget
- **new** `frontend/src/components/take/TrueFalseQuestion.test.tsx` — tests
- **edit** `frontend/src/components/take/TestRunner.tsx` — dispatch
- **edit** `docs/features/w5-f3-legacy-true-false-rendering.md` — check off steps
- **edit** `docs/FEATURE_STATUS.md` — flip row to ✅
- **edit** `docs/technical-debt.md` — §7 cross-referenced as closed (+ correct the
  "only stale volumes" claim)

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create **`richardh-feat-W5F3`** off `richardh` before any code change.
- **First commit on the branch = this plan file.**
- One commit per milestone (Conventional Commits).

## Milestones

### M1 — `TrueFalseQuestion` take widget
- New `frontend/src/components/take/TrueFalseQuestion.tsx`, matching take-leaf
  conventions (props `{ question, selected: number[], onChange, disabled,
  labelledBy }` — same contract as `SingleSelectQuestion`).
- Render True/False as a `RadioGroup` (a11y parity with `labelledBy` /
  `disabled`, consistent with W3-F7). **Mapping: True ↔ `[1]`, False ↔ `[0]`.**
  Derive current selection from `selected` (`selected.includes(1)` → True,
  `selected.includes(0)` → False, else none).
- No "no options available" path — the widget *is* the option-less renderer.
- **Commit:** `feat(take): add TrueFalseQuestion widget for option-less true_false`

### M2 — Wire dispatch in `TestRunner`
- In `renderQuestion` add a `case 'true_false'`: when `options` is absent/empty →
  `TrueFalseQuestion`; when a true_false doc *does* carry options (defensive,
  e.g. legacy-with-options) → keep `SingleSelectQuestion`. `mcq` stays on the
  `default` → `SingleSelectQuestion` branch unchanged.
- **Commit:** `feat(take): route option-less true_false to TrueFalseQuestion`

### M3 — Frontend tests
- New `TrueFalseQuestion.test.tsx` (vitest + @testing-library, matching
  `SingleSelectQuestion.test.tsx` style):
  - option-less true_false doc → renders True & False, **no error text**;
  - click True → `onChange([1])`; click False → `onChange([0])`;
  - `selected=[1]` reflects True selected; `disabled` blocks interaction.
- Add/extend a TestRunner-or-dispatch test asserting an option-less true_false no
  longer shows "No options available" and a current-shape mcq still renders its
  options unchanged.
- **Commit:** `test(take): cover option-less true_false render + answer mapping`

### M4 — Docs, debt note, status flip
- Check off detail-doc steps with evidence (file:line, commit).
- `FEATURE_STATUS.md` row → ✅.
- `technical-debt.md` §7: mark closed **and correct** the "only stale volumes"
  claim (note true_false is canonically option-less). Add the seed-data
  inconsistency as a flagged note (deferred to a data/seed fix, not this render
  feature).
- **Commit:** `docs(W5-F3): mark complete; correct debt §7; flag seed encoding defect`

## Testing & validation

- `cd frontend && pnpm test` (vitest) — new + existing suites green.
- `cd frontend && pnpm lint` — clean.
- `cd frontend && pnpm build` — typechecks/builds clean.
- **Pass bar:** all three green; no new errors. (No backend change → no pytest
  delta; scoring works via existing exact-match bool↔int equality, asserted by
  reasoning above and unchanged backend tests.)

## Requirements review (final milestone)

Re-read detail-doc **Steps** + **Acceptance** against the diff:
- Step 1 approach picked (a) — ✅ documented here.
- Step 2 implement: legacy/option-less + current-with-options both render and
  score (True→[1]/False→[0] ⇒ set-equality with `[true]`/`[false]`).
- Step 3 frontend tests green.
- Step 4 normalization not used (approach a) → seed defect flagged, not mutated.
- Acceptance: working True/False control (not the error); tests + lint + build
  green; FEATURE_STATUS ✅; debt §7 cross-referenced.

## Push gate

Push `richardh-feat-W5F3` **only if** `pnpm test` + `pnpm lint` + `pnpm build`
pass **and** every Step/Acceptance item is confirmed. Otherwise stop and report
what's outstanding.

## Post-push

Best-effort KG re-ingest (`tools/knowledge-graph/`: `kg.py up && ingest &&
down`). Skip + note if Docker/models unavailable — Layer 1 is live regardless.
