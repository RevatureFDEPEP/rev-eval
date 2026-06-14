# W2-F6 — Structured Question Authoring Interface

**Status:** 🟡 In Progress
**Spec:** `days_6_10_features.md` §6 (Day 9)
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton — question documents must exist in MongoDB)
**Last updated:** 2026-06-12

Interactive Next.js form letting trainers author questions into MongoDB.

## Steps

- [x] **1. Create page** —
      `frontend/src/app/(dashboard)/trainer/questions/create/page.tsx` and
      question list `frontend/src/app/(dashboard)/trainer/questions/page.tsx`
      exist as brownfield pages. Live at `/trainer/questions/create` (matches
      the repo's role-dashboard convention: `TRAINER`/`ADMIN` → `/trainer`).
- [ ] **2. Shared QuestionForm component** — extract the inline form from the
      create page into `frontend/src/components/trainer/QuestionForm.tsx` with
      react-hook-form + `useFieldArray`; fields switch per type (MCQ/MULTI
      options arrays vs. TRUE_FALSE checkbox). File does not exist yet.
- [x] **3. Zod validation schema** — `frontend/src/lib/schemas/question-form.ts`
      with `buildQuestionSchema(questionType)` rules per type. Covered by
      `frontend/src/__tests__/lib/schemas/question-form.test.ts` (tianyac,
      commit `e9c179a`).
- [ ] **4. Submit via gateway** — validated payload POSTed through the API
      gateway to question-management-service. Depends on step 2 (shared form)
      and [W2-F5](w2-f5-minio-presigned-uploads.md) for file-upload field.

## Evidence

- Schema: `frontend/src/lib/schemas/question-form.ts`.
- Tests: `frontend/src/__tests__/lib/schemas/question-form.test.ts` (135 lines,
  commit `e9c179a`).
- Lint/TS fixes to existing trainer pages: commits `2c35942`, `2df7178`,
  `895ccb4`, `1a5399f`.

## Remaining

- Extract `QuestionForm.tsx` shared component from the create page (step 2).
- Wire validated submit through the API gateway (step 4).
- File upload field — blocked on [W2-F5](w2-f5-minio-presigned-uploads.md).
- Edit page `trainer/questions/edit/[id]/page.tsx`.
