# W2-F6 — Structured Question Authoring Interface

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §6 (Day 9)
**Unblocks:** W3-F3 (Test-Taking Frontend Skeleton — question documents must exist in MongoDB)
**Last updated:** 2026-06-09

Interactive Next.js form letting trainers author questions into MongoDB.

## Steps

- [x] **1. Create page** —
      `frontend/src/app/(dashboard)/trainer/questions/create/page.tsx`. Lives
      at `/trainer/questions/create` rather than the spec's `/admin/...` —
      matches the repo's role-dashboard convention (`TRAINER`/`ADMIN` →
      `/trainer`). **Caveat:** the create page is **inherited brownfield**; this
      PR only extracts it into the shared `QuestionForm`, it did not author the
      page. Student alexis #59 is the more literal W2-F6 (real
      `/admin/...create`).
- [x] **2. Dynamic form by question type** —
      `frontend/src/components/trainer/QuestionForm.tsx`: react-hook-form +
      `useFieldArray`; fields switch per type (options arrays for MCQ/MULTI vs.
      TRUE_FALSE checkbox). Extracted from the create page (commit `566ba9d`)
      with utils in `question-form-utils.ts`.
- [x] **3. Zod validation schema** — `zodResolver` with dynamic
      `buildQuestionSchema(mode, questionType)`: non-empty option text; MULTI
      "at least one, but not all" enforced at **both** create and edit via a
      shared refine (`createMultiSchema`/`editMultiSchema`). **Design note:** the
      create flow is built around mcq→multi **auto-promotion**, so create-mcq is
      intentionally *lenient* (≥1 correct, promotes to multi when 2+ checked) and
      the "MCQ exactly one" rule is enforced only at edit. Multi-select is now a
      first-class create type (`?type=multi`) rather than a side-effect of that
      promotion. This diverges from alexis #59, which enforces mcq-exactly-one at
      create via `superRefine` (no auto-promotion).
- [x] **4. Submit via gateway** — validated payload POSTed through the API
      gateway to question-management-service.

## Beyond spec

- Question list page (`trainer/questions/page.tsx`).
- Edit page `trainer/questions/edit/[id]/page.tsx` (commit `422e0db`, branch
  `richardh-feat-questions`).
- Unit tests for form utils (commit `908dcb6`) — see
  [W2-F2](w2-f2-unit-test-scaffolding.md).

## Remaining

None blocking. Two accepted deviations from the literal spec:

- **mcq exactly-one at create is intentionally not enforced** — mcq→multi
  auto-promotion is the chosen design; multi-select is instead a first-class
  create type with its own strict schema (commit `fb80157`, `6460fa5`).
- The create page lives at `/trainer/questions/create` (role-dashboard
  convention) rather than the spec's `/admin/...`, and is the extracted
  brownfield page — both deviate by design.

(File-upload field belongs to [W2-F5](w2-f5-minio-presigned-uploads.md).)
