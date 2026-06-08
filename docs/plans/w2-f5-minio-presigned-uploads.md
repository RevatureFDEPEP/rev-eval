# W2-F5 — Direct-to-MinIO Diagram Uploads via Pre-Signed URLs

## Context

W2-F5 (`docs/features/w2-f5-minio-presigned-uploads.md`, spec `days_6_10_features.md` §5, Days 8–9) lets question authors attach diagrams/screenshots: browser fetches a pre-signed PUT URL from question-management-service, uploads the file directly to MinIO, and the object key is stored on the question's Mongo document. Currently ❌ Not Started; it unblocks W3-F1 (quiz sessions need seeded question docs). `src/utils/s3_client.py` is already seeded with `generate_presigned_put_url` / `generate_presigned_get_url` / `ensure_bucket` (boto3, sigv4) — unused. User opted **in** to the edit-form preview extension (presigned GET `image_url` in responses); quiz/participant display stays out of scope.

## Key design decisions

- **Signing-host fix (critical):** SigV4 binds `Host` into the signature, so a URL signed against `http://minio:9000` fails when the browser hits `localhost:9000`. Add setting `S3_PUBLIC_ENDPOINT_URL` (default `http://localhost:9000`) and a **second boto3 client used only for presigning** (presigning is offline — unreachable host is fine). Internal client (`http://minio:9000`) keeps `ensure_bucket`.
- **Gateway: no change.** Existing `^/v1/api/questions(/.*)?$` in `services/api-gateway-service/main.py` already matches the new endpoint — verify only, check off step 2 in the detail doc.
- **Route ordering (critical):** declare `GET /presigned-upload-url` **before** `GET /{id}` in `question_routes.py` or `/{id}` captures it.
- **Server generates object key** `questions/{uuid4.hex}.{ext}`; extension derived from validated content_type (`image/png`→png, `image/jpeg`→jpg), never from client filename.
- **Direct MinIO PUT bypasses BFF/`api` client** — raw `fetch`, no credentials; `Content-Type` header must exactly match signed type or `SignatureDoesNotMatch`.
- **CORS:** pin `MINIO_API_CORS_ALLOW_ORIGIN` in compose (modern MinIO defaults `*`, pin anyway).
- **Orphan objects** (upload then abandon form / re-select file) — accepted limitation, document, don't build cleanup.

## Branch & commit plan

Feature branch off `richardh` following the established pattern (cf. `richardh-feat-linting`, PR #40): **`richardh-feat-minio-uploads`**. PR back into `richardh`. Regular commits at each logical boundary (conventional-commit style, matching repo history):

1. `docs(plans): add W2-F5 MinIO presigned uploads implementation plan` — plan file under `docs/plans/` (first commit, before code).
2. `feat(question-service): presigned upload URL endpoint + public signing endpoint` — steps 1–6 backend.
3. `feat(question-service): image_object_key on question document + schemas` — step 7 (+ schema parts of 5 if not already in #2).
4. `chore(compose): MinIO CORS pin + S3_PUBLIC_ENDPOINT_URL env` — step 8.
5. `feat(frontend): question diagram upload via presigned PUT` — steps 9–12.
6. `test(question-service): presign upload service unit tests` — step 13.
7. `docs: mark W2-F5 completed in feature tracker` — steps 14–15.

## Backend (services/question-management-service/)

1. **`src/config/settings.py`** (after S3 block ~line 42): add
   `S3_PUBLIC_ENDPOINT_URL: str = "http://localhost:9000"` with comment explaining SigV4 host binding.
2. **`src/utils/s3_client.py`**: add `s3_presign_client` (same creds/region/sigv4, `endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL`); switch `generate_presigned_put_url` and `generate_presigned_get_url` to use it. `ensure_bucket` stays on internal client.
3. **`main.py`** startup (after `await init_db()`): call `ensure_bucket()` in try/except logging a warning on failure (no `mc` init container exists; this is the only bucket creation).
4. **NEW `src/services/upload_service.py`**: `UploadService.presigned_question_image_upload(content_type)` — validate content_type against `{"image/png": "png", "image/jpeg": "jpg"}` (400 otherwise), build key `questions/{uuid4().hex}.{ext}`, return `{upload_url, object_key, expires_in}`.
5. **`src/schemas/question.py`**:
   - NEW `PresignedUploadResponse(upload_url: str, object_key: str, expires_in: int)`.
   - `QuestionCreate` / `QuestionUpdate`: `image_object_key: Optional[str] = Field(None, max_length=256)`.
   - `QuestionResponse`: `image_object_key: Optional[str]` + `image_url: Optional[str]` (presigned GET, populated when key present).
6. **`src/v1/routes/question_routes.py`**: `GET /presigned-upload-url` (`response_model=PresignedUploadResponse`, `content_type` query param) inserted **between** `get_all_questions` and `get_question_by_id`. Where `QuestionResponse` is built, enrich `image_url = generate_presigned_get_url(key)` when `image_object_key` set (follow however responses are assembled — route or service layer; keep consistent).
7. **`src/models/question.py`** `Question` document (after `tags` ~line 77): `image_object_key: Optional[str] = Field(default=None, max_length=256)`. Create/update flows use `model_dump()` / non-None-field updates, so field flows through with no service/repo change.

## Compose / env

8. **`docker-compose.yml`**: minio env → `MINIO_API_CORS_ALLOW_ORIGIN: "http://localhost:3000"`; question-management-service env → `S3_PUBLIC_ENDPOINT_URL: ${S3_PUBLIC_ENDPOINT_URL:-http://localhost:9000}`. Mirror key in `.env.example`. No new ports (9000 already published).

## Frontend (frontend/)

9. **`src/lib/api/types.ts`**: `QuestionCreate` + `Question` get `image_object_key?: string`; `Question` also `image_url?: string`; NEW `PresignedUpload {upload_url, object_key, expires_in}`.
10. **`src/lib/api/questions.ts`**:
    - `getPresignedUploadUrl(contentType)` → `api.get` `/v1/api/questions/presigned-upload-url?content_type=...` (BFF proxy forwards query params already).
    - `uploadToPresignedUrl(uploadUrl, file)` → raw `fetch` PUT, body=file, header `Content-Type: file.type`, throw on `!res.ok`.
11. **`src/components/trainer/question-form-utils.ts`**: base Zod schema gains optional `image` (File; `image/png|image/jpeg` only; ≤ 5 MB — `5 * 1024 * 1024`) and `image_object_key: z.string().optional()`. `transformFormData` emits `image_object_key`; `QuestionFormInitial` + `toInitial` carry it (and `image_url` for preview) for edit mode.
12. **`src/components/trainer/QuestionForm.tsx`**: new Card after Question Text — shadcn `<Input type="file" accept="image/png,image/jpeg">`. On select: client-side guard (type/size, mirrors Zod) → `getPresignedUploadUrl(file.type)` → `uploadToPresignedUrl` → `form.setValue("image_object_key", object_key)`; `uploading` state disables input; errors via `form.setError("image", ...)`. Preview: render `<img>` from local `URL.createObjectURL(file)` after upload, or `initialData.image_url` in edit mode. Parent create/edit pages unchanged (payload flows via `transformFormData`).

## Tests

13. **`services/question-management-service/tests/test_upload_service.py`** (tests/ exists from W2-F2; mock/patch `generate_presigned_put_url`, no Mongo):
    - png → key matches `^questions/[0-9a-f]{32}\.png$`, response shape correct.
    - jpeg → `.jpg` extension.
    - `application/pdf`, `image/gif` → HTTPException 400.
    Frontend: no test runner — skip.

## Docs (same PR — project workflow rule)

14. `docs/features/w2-f5-minio-presigned-uploads.md`: check off steps 1–6, status ✅, evidence (paths/PR), note signing-host decision + orphan-object limitation.
15. `docs/FEATURE_STATUS.md` line 34: W2-F5 row → ✅ Completed; bump "Last assessed".
16. Save this plan to `docs/plans/w2-f5-minio-presigned-uploads.md` as the **first commit** on the feature branch (version-controlled plans rule).

## Verification

1. `docker compose up --build`; question-management-service logs show bucket ensured, no startup errors.
2. MinIO console `http://localhost:9001` (minioadmin/minioadmin) → `question-images` bucket exists.
3. `http://localhost:3000`, login seeded trainer (`password123`), trainer → create question.
4. Select small `.png`: network shows `GET .../presigned-upload-url?content_type=image/png` 200 then direct `PUT http://localhost:9000/question-images/questions/<uuid>.png` 200; preview renders.
5. `.gif` and >5 MB file → rejected client-side, no PUT fired.
6. Submit; `docker compose exec mongo mongosh evalai --eval 'db.questions.find().sort({_id:-1}).limit(1)'` → `image_object_key` stored.
7. Edit same question → `image_url` preview renders (presigned GET round-trip).
8. `cd services/question-management-service && pytest tests/` green.
