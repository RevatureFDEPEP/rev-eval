# W2-F6 — Structured Question Authoring Interface

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §6 (Day 9)
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton — question documents must exist in MongoDB)
**Last updated:** 2026-06-04

Interactive Next.js form letting trainers author questions into MongoDB.

## Steps

- [x] **1. Create page** —
      `frontend/src/app/(dashboard)/trainer/questions/create/page.tsx`. Lives
      at `/trainer/questions/create` rather than the spec's `/admin/...` —
      matches the repo's role-dashboard convention (`TRAINER`/`ADMIN` →
      `/trainer`).
- [x] **2. Dynamic form by question type** —
      `frontend/src/components/trainer/QuestionForm.tsx`: react-hook-form +
      `useFieldArray`; fields switch per type (options arrays for MCQ/MULTI vs.
      TRUE_FALSE checkbox). Extracted from the create page (commit `566ba9d`)
      with utils in `question-form-utils.ts`.
- [x] **3. Zod validation schema** — `zodResolver` with dynamic
      `buildQuestionSchema(mode, questionType)`: MCQ exactly one correct
      answer, MULTI at least one, non-empty option text.
- [x] **4. Submit via gateway** — validated payload POSTed through the API
      gateway to question-management-service.

## Beyond spec

- Question list page (`trainer/questions/page.tsx`).
- Edit page `trainer/questions/edit/[id]/page.tsx` (commit `422e0db`, branch
  `richardh-feat-questions`).
- Unit tests for form utils (commit `908dcb6`) — see
  [W2-F2](w2-f2-unit-test-scaffolding.md).

## Remaining

None. (File-upload field belongs to [W2-F5](w2-f5-minio-presigned-uploads.md).)
