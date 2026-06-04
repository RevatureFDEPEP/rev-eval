# Question Authoring: Edit Page + Shared QuestionForm

## Context

The trainer question authoring interface (spec W2-F6, `days_6_10_features.md`) is partially built in the brownfield: a working create form exists at `frontend/src/app/(dashboard)/trainer/questions/create/page.tsx` (~740 lines, react-hook-form + zod, dynamic per question type). However, `QuestionDetailsSheet.tsx` links to `/trainer/questions/edit/{id}`, which **404s — no edit page exists**. Goal: add the edit page by extracting the create form into a shared `QuestionForm` component used by both pages, completing the authoring CRUD loop. (Image upload / W2-F5 deliberately out of scope per user decision.)

## Backend constraints (verified)

`services/question-management-service`:
- `PUT /v1/api/questions/{id}` takes `QuestionUpdate` — **all fields optional, partial update**. Fields sent as `null` are skipped (`{k: v for ... if v is not None}` in `src/services/question_service.py:123`); empty `[]`/`""` DO get applied.
- **`type` is immutable** — `QuestionUpdate` schema has no `type` field; Pydantic silently drops it if sent. Service validates the update against the *stored* type (`_validate_update_for_type`).
- Validation per stored type (`question_service.py:160-230`):
  - `mcq`: exactly 1 int correct answer, 2+ options
  - `multi`: **≥1** correct answer (line 198), **not all** options correct (line 219), no duplicates, 2+ options
  - `true_false`: single boolean in `correct_answers`, no options
  - `text`: `sample_answer` ≥10 chars, no options/correct_answers
- Consequence: **mcq↔multi auto-promotion (create-mode behavior) cannot apply on edit** — form must enforce the loaded type's rule client-side or backend 400s.
- GET response: `options: [{option_id (1-indexed int), text}]`, `correct_answers: [int] | [bool] | null`, `tags`/`skills` string arrays.
- PUT returns `{message, id}`, not the Question — `updateQuestion()`'s `Promise<Question>` typing is a pre-existing harmless mismatch; ignore return value.

## Files

1. **NEW** `frontend/src/components/trainer/QuestionForm.tsx` — extracted shared form (JSX + react-hook-form wiring only)
2. **NEW** `frontend/src/components/trainer/question-form-utils.ts` — pure logic: zod schema builder, `transformFormData`, `toInitial`, default values (extracted so it's unit-testable without rendering)
3. **NEW** `frontend/src/app/(dashboard)/trainer/questions/edit/[id]/page.tsx` — edit page
4. **REFACTOR** `frontend/src/app/(dashboard)/trainer/questions/create/page.tsx` — thin wrapper
5. **NEW** test infra: `frontend/vitest.config.ts`, `frontend/src/components/trainer/__tests__/question-form-utils.test.ts`; `package.json` devDeps + `"test": "vitest run"` script
6. Reference (no change): `frontend/src/lib/api/questions.ts` (`getQuestion`, `updateQuestion`, `createQuestion` already exist), `frontend/src/lib/api/types.ts`

## Step 0 — Test infra (Vitest)

Frontend has **no test runner** (`pnpm test` absent; CI runs it `--if-present`). Add:
- devDeps: `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`
- `frontend/vitest.config.ts`: react plugin, `environment: "jsdom"`, `@` path alias matching tsconfig
- `package.json` script: `"test": "vitest run"` — this also activates the existing CI `pnpm test --if-present` step

## Step 1 — Extract `QuestionForm.tsx` + `question-form-utils.ts`

Pure logic goes to `question-form-utils.ts` (no React imports): zod schemas/builder, `transformFormData(values, mode, questionType)`, `toInitial(q)`, `getDefaultValues(type)`. `QuestionForm.tsx` keeps only JSX + hooks and imports from utils.

Move from create page into `src/components/trainer/QuestionForm.tsx` (`"use client"`):
- All zod schemas (`baseSchema`, `mcqSchema`, `trueFalseSchema`, `textSchema`) + form value types
- The full `<Form>` JSX (create page lines 314–738), skills-loading `useEffect`, `useFieldArray`, skill search state, `transformFormData`
- Carry over the `// eslint-disable-next-line @typescript-eslint/no-explicit-any` on `useForm<any>`

Props:

```ts
interface QuestionFormProps {
  mode: "create" | "edit";
  questionType: QuestionType;          // create: from ?type=; edit: from loaded question
  initialData?: QuestionFormInitial;   // edit only — pre-mapped form values
  onSubmit: (data: QuestionCreate) => Promise<void>; // page owns API call + toast + redirect
  submitting: boolean;
  error: string | null;
}

interface QuestionFormInitial {
  question_text: string;
  difficulty?: QuestionDifficulty;
  skills: string[];
  tags: string;                                       // comma string for the input
  answer_explanation: string;
  options?: { text: string; is_correct: boolean }[];  // mcq/multi
  true_false_answer?: boolean;                        // true_false
  sample_answer?: string;                             // text
}
```

Mode differences inside the component:
- Header title: "Create New Question" vs "Edit Question"; button: "Create Question"/"Creating..." vs "Save Changes"/"Saving..."
- `defaultValues: initialData ?? getDefaultValues()` — edit page mounts the form **only after data loads**, so `useForm` snapshots correct defaults (no `form.reset` dance)
- Options card JSX condition: extend `questionType === "mcq"` → `questionType === "mcq" || questionType === "multi"` (multi questions reuse same options+checkbox UI)
- Schema selection becomes mode/type-aware (Step 3)
- Preserve the tags zod `.transform` + the `typeof values.tags === "string" ? [] : values.tags` guard in `transformFormData` exactly — load-bearing

## Step 2 — Refactor create page

Shrinks to: `useRouter`, `useSearchParams`, `submitting`/`error` state, `questionType` from `?type=` (default `"mcq"`), `onSubmit` calling `createQuestion(data)` + existing toast + `router.push("/trainer/questions")`, render `<QuestionForm mode="create" ... />`. **Behavior byte-for-byte identical**, incl. mcq→multi auto-promotion at submit.

## Step 3 — Edit-mode validation & submit semantics

In `transformFormData` / schema builder:
- **create**: unchanged — 1 checked → `type: "mcq"`, 2+ → `"multi"`
- **edit**: don't rely on type promotion; enforce loaded type:
  - loaded `mcq` → zod refine: **exactly one** `is_correct`
  - loaded `multi` → zod refine: **≥1 correct AND not all** options correct (matches backend lines 198/219 — NOT "2+")
  - `true_false`/`text`: same transforms as create
- Including `type` in the PUT payload is harmless (backend drops it); simplest to keep `transformFormData` output shape unchanged

## Step 4 — Edit page

`frontend/src/app/(dashboard)/trainer/questions/edit/[id]/page.tsx` (`"use client"`), mirroring `tests/edit/[testId]/page.tsx` conventions:
1. `const { id } = useParams()` (client hook — same as tests edit page; avoids params-Promise issue)
2. `useEffect`: `getQuestion(id)` → map via `toInitial()` (Step 5) → set `initialData` + `questionType`; 404 → `notFound` state; other errors → `error`
3. Render branches: loading spinner → not-found card with back link to `/trainer/questions` → error card → `<QuestionForm mode="edit" questionType initialData onSubmit={handleUpdate} ... />`
4. `handleUpdate`: `await updateQuestion(id, data)`, success toast, `router.push("/trainer/questions")`, try/catch → `setError`

## Step 5 — Mapping helper

```ts
function toInitial(q: Question): { type: QuestionType; data: QuestionFormInitial } {
  const base = {
    question_text: q.question_text,
    difficulty: q.difficulty,
    skills: q.skills ?? [],
    tags: (q.tags ?? []).join(", "),
    answer_explanation: q.answer_explanation ?? "",
  };
  if (q.type === "mcq" || q.type === "multi") {
    const correct = new Set((q.correct_answers ?? []) as number[]); // 1-indexed option_ids
    return { type: q.type, data: { ...base,
      options: (q.options ?? []).map(o => ({ text: o.text, is_correct: correct.has(o.option_id) })),
    }};
  }
  if (q.type === "true_false") {
    return { type: "true_false", data: { ...base, true_false_answer: q.correct_answers?.[0] as boolean } };
  }
  return { type: "text", data: { ...base, sample_answer: q.sample_answer ?? "" } };
}
```

Key `is_correct` off `option_id` (robust to ordering); submit transform maps back by array index + 1 — consistent since backend assigns option_ids by position.

## Step 6 — Unit tests

`frontend/src/components/trainer/__tests__/question-form-utils.test.ts`:
- **`toInitial`**: all 4 types — mcq/multi options map `is_correct` by `option_id`, true_false boolean extraction, text `sample_answer`, tags array → comma string, null/missing field defaults
- **`transformFormData`**:
  - create mode: 1 correct → `type: "mcq"`, 2+ correct → `"multi"`; 1-indexed `correct_answers`; tags string-guard behavior; true_false → `[bool]`; text → no options/correct_answers
  - edit mode: type preserved (no promotion), payload shape matches `QuestionUpdate`
- **schema builder** (zod `safeParse`): edit-mcq rejects 0 and 2+ correct; edit-multi rejects 0 correct and all-correct, accepts 1; create-mcq accepts ≥1 (promotion path); question_text <10 chars rejected; text sample_answer <10 rejected

Run: `cd frontend && pnpm test`.

## Commit plan (branch `richardh-feat-questions`, commit after each step passes lint+tests)

1. `test(frontend): add vitest + testing-library setup` — Step 0
2. `refactor(frontend): extract QuestionForm + form utils from create page` — Steps 1–2 (create behavior unchanged)
3. `test(frontend): unit tests for question form utils` — Step 6 (covers extracted logic before edit feature lands)
4. `feat(frontend): question edit page at /trainer/questions/edit/[id]` — Steps 3–5 + edit-mode tests

## Risks

- `useForm` snapshots defaults on mount → MUST gate `QuestionForm` render behind loading flag in edit page
- Multi questions need the options card condition extended, else blank form on edit
- Edit-multi refine must be ≥1-not-all (backend rule), not exactly-one or 2+
- Don't depend on `updateQuestion` return value (actual response is `{message, id}`)

## Verification

1. `cd frontend && pnpm lint && pnpm test && pnpm build`
2. `docker compose up --build`; seed: `python services/question-management-service/seed_rag_context_questions.py`
3. Login as trainer (`password123`) → questions list → details sheet → Edit:
   - All 4 types pre-populate correctly (mcq, multi, true_false, text)
   - Change a field, save → redirect, reopen → change persisted
   - mcq edit: blocking validation if 0 or 2+ correct checked; multi edit: blocked if 0 or all correct
4. Regression: create page still works for all types incl. mcq→multi promotion
