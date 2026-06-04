# F5 — Direct-to-MinIO Diagram Uploads via Pre-Signed URLs

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` §5 (Days 8–9)
**Unblocks:** W3-F1 (Quiz Session Creation Backend — needs seeded question documents for `$sample` aggregation)
**Last updated:** 2026-06-04

Let question authors upload diagrams/screenshots directly from the browser to
MinIO via pre-signed PUT URLs, storing the object key on the question document.

## Steps

- [ ] **1. Pre-signed URL endpoint** — `GET /questions/presigned-upload-url` in
      question-management-service using boto3 to generate a pre-signed PUT URL
      for MinIO.
- [ ] **2. Gateway route** — add the endpoint's URL pattern to `ROUTES` in
      `services/api-gateway-service/main.py` (services are not auto-discovered).
- [ ] **3. Question document field** — add image/object-key field to the
      question Beanie document
      (`services/question-management-service/src/models/`).
- [ ] **4. Frontend file input** — file-input field in the question form
      (`frontend/src/components/trainer/QuestionForm.tsx`).
- [ ] **5. Client-side validation** — Zod: `.png`/`.jpg` only, ≤ 5 MB.
- [ ] **6. Direct upload flow** — on file select: fetch pre-signed URL, browser
      PUTs directly to MinIO, save object key/path in the question's MongoDB
      document on submit.

## Existing assets

- `services/question-management-service/src/utils/s3_client.py` — seeded MinIO
  client helper, currently unused (no route imports it). Start here.
- MinIO runs in compose (:9000, console :9001, creds `minioadmin`/`minioadmin`).
- Question form already componentized ([F6](f6-question-authoring-ui.md)) —
  file input slots into `QuestionForm`.

## Remaining

All steps.
