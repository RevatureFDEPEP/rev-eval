# W2-F5 — Direct-to-MinIO Diagram Uploads via Pre-Signed URLs

**Status:** ❌ Not Started
**Spec:** `days_6_10_features.md` §5 (Days 8–9)
**Unblocks:** W3-F1 (Quiz Session Creation Backend — needs seeded question documents for `$sample` aggregation)
**Last updated:** 2026-06-12

Let question authors upload diagrams/screenshots directly from the browser to
MinIO using pre-signed PUT URLs, avoiding gateway as a data proxy.

## Steps

- [ ] **1. Pre-signed URL endpoint** — `question-management-service`:
      `POST /questions/upload-url` returns a short-lived pre-signed PUT URL for
      a given filename.
- [ ] **2. Gateway route** — expose the endpoint at `/v1/questions/upload-url`.
- [ ] **3. Question document field** — add optional `image_url` field to the
      `Question` Beanie document.
- [ ] **4. Frontend file input** — file input in the question authoring form
      that triggers the pre-signed URL flow.
- [ ] **5. Client-side validation** — type (image/*) and size limits before
      requesting the pre-signed URL.
- [ ] **6. Direct upload flow** — browser PUTs directly to MinIO using the
      pre-signed URL; on success, stores the MinIO object URL in form state.

## Evidence

None on `tianyac` branch.

Note: another contributor delivered this feature on branch
`richardh-feat-minio-uploads` (PR #49); that work is not yet merged into
`tianyac`.

## Remaining

All steps. Also depends on MinIO service being wired in `docker-compose.yml`.
Unblocks the file-upload field in [W2-F6](w2-f6-question-authoring-ui.md).
