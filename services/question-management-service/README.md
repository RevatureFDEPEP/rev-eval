# Question Management Service

A FastAPI service on port **8003** that owns the question bank. Questions are stored in MongoDB (Beanie ODM) and question images are stored in MinIO (S3-compatible).

## Question types

| Type | Shape |
|------|-------|
| `mcq` | one correct option out of at least two |
| `multi` | several correct options |
| `true_false` | a boolean answer |
| `text` | free text with a sample answer |

Questions also carry skills, tags, difficulty and an optional answer explanation. The question type cannot be changed after creation.

## Endpoints

Under `/v1/api/questions`, reached through the API gateway. Every route requires a Bearer JWT; create, update, delete and the image upload URL require the `TRAINER` role. Read routes return the answer fields (`correct_answers`, `sample_answer`, `answer_explanation`) only to trainers and to test-management-service, which identifies itself with the shared `INTERNAL_SERVICE_TOKEN` to score submissions; participants get questions without them.

- CRUD: `POST /`, `GET /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`
- Filtering: `GET /filter` (combined criteria), `/by-type/{type}`, `/by-skill/{skill}`, `/by-difficulty/{difficulty}`, `/by-tags`
- Images: `POST /{id}/image/upload-url` and `GET /{id}/image/download-url` return pre-signed MinIO URLs, so image bytes never pass through the service
- `GET /health`, and Swagger UI at `/docs`

## Layout

`src/models` (Beanie documents), `src/schemas` (request and response models), `src/repositories` (MongoDB access), `src/services` (validation and business rules), `src/v1/routes` (API), `src/utils` (JWT/role dependencies and the S3 client).

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). Configuration comes from environment variables (`MONGO_URI`, `MONGO_DB`, `S3_*`, `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `PORT`).

```bash
cd services/question-management-service
pip install -r requirements.txt pytest pytest-cov
pytest        # unit, JWT and MongoDB integration tests; fails below 80 % coverage
```
