# F5 — Direct-to-MinIO Diagram Uploads via Pre-Signed URLs

**Status:** ✅ Completed
**Spec:** `days_6_10_features.md` §5 (Days 8–9)
**Unblocks:** W3-F1 (Quiz Session Creation Backend — needs seeded question documents for `$sample` aggregation)
**Last updated:** 2026-06-05 (branch `richardh-feat-minio-uploads`)

Let question authors upload diagrams/screenshots directly from the browser to
MinIO via pre-signed PUT URLs, storing the object key on the question document.

Implementation plan: [docs/plans/f5-minio-presigned-uploads.md](../plans/f5-minio-presigned-uploads.md)

## Steps

- [x] **1. Pre-signed URL endpoint** — `GET /questions/presigned-upload-url` in
      question-management-service using boto3 to generate a pre-signed PUT URL
      for MinIO.
      Evidence: `src/services/upload_service.py` (new),
      `src/v1/routes/question_routes.py` (declared *before* `/{id}` so the
      path param doesn't capture it). Server generates the object key
      (`questions/{uuid}.{ext}`); content type validated server-side
      (png/jpeg only → 400 otherwise).
- [x] **2. Gateway route** — verified no change needed: the existing
      `^/v1/api/questions(/.*)?$` pattern in
      `services/api-gateway-service/main.py` already matches the new endpoint.
- [x] **3. Question document field** — `image_object_key` added to the
      `Question` Beanie document (`src/models/question.py`) and to
      `QuestionCreate` / `QuestionUpdate` / `QuestionResponse` schemas.
      Responses are enriched with a pre-signed GET `image_url` when a key is
      set (`_to_response` in `question_routes.py`).
- [x] **4. Frontend file input** — "Diagram or Screenshot" card in
      `frontend/src/components/trainer/QuestionForm.tsx` with preview,
      remove button, and upload spinner.
- [x] **5. Client-side validation** — Zod `imageFileSchema` in
      `question-form-utils.ts`: `.png`/`.jpg` only, ≤ 5 MB.
- [x] **6. Direct upload flow** — on file select: fetch pre-signed URL via
      BFF/gateway (`getPresignedUploadUrl`), browser PUTs directly to MinIO
      (`uploadToPresignedUrl` — deliberately bypasses the BFF; no
      cookies/Bearer), object key stored in form state and persisted on the
      question document on submit.

## Design notes

- **Signing host:** SigV4 binds the `Host` header into the signature, so URLs
  signed against the in-network endpoint (`http://minio:9000`) fail when the
  browser uploads via `localhost:9000`. A second boto3 client
  (`s3_presign_client` in `src/utils/s3_client.py`) signs against the new
  `S3_PUBLIC_ENDPOINT_URL` setting (default `http://localhost:9000`);
  presigning is offline, so the unreachable-from-container host is fine. The
  internal client still handles `ensure_bucket()`, which now runs at service
  startup (no `mc` init container exists).
- **CORS:** `MINIO_API_CORS_ALLOW_ORIGIN` pinned to the frontend origin in
  `docker-compose.yml`.
- The `Content-Type` header on the browser PUT must exactly match the signed
  content type or MinIO returns `SignatureDoesNotMatch`.

## Known limitations (accepted)

- **Orphan objects:** an upload followed by an abandoned form (or re-selecting
  a different file) leaves an unreferenced object in the bucket. No cleanup
  is built — acceptable for local-first dev.
- Image display in quiz/participant components is out of scope for F5; only
  the trainer form preview consumes `image_url`.

## Verification (performed 2026-06-05)

- `question-management-service` startup log: `Created S3 bucket question-images`.
- `GET /v1/api/questions/presigned-upload-url?content_type=image/png` → 200
  with `upload_url` / `object_key` / `expires_in`; `image/gif` → 400.
- Browser-style `PUT` of a PNG to the signed `localhost:9000` URL → 200.
- Question created with `image_object_key` → `GET /questions/{id}` returns the
  key and a working pre-signed `image_url` (GET → 200).
- `pytest tests/` — 16 passed (includes new `test_upload_service.py`).
- `ruff check` and `pnpm lint` / `tsc --noEmit` clean.
