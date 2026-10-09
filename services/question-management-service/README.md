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

Under `/v1/api/questions`, reached through the API gateway. The question bank is trainer-only: every read route and the image download URL require a `TRAINER` JWT or test-management-service's shared `INTERNAL_SERVICE_TOKEN`, which it uses to score submissions; any other caller, a participant included, gets `403`. Create, update, delete and the image upload URL require the `TRAINER` role. Participants receive their quiz questions from test-management-service, without answer keys.

- CRUD: `POST /`, `GET /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`
- Filtering: `GET /filter` (combined criteria), `/by-type/{type}`, `/by-skill/{skill}`, `/by-difficulty/{difficulty}`, `/by-tags`
- Images: `POST /{id}/image/upload-url` and `GET /{id}/image/download-url` return pre-signed MinIO URLs, so image bytes never pass through the service
- `GET /health`, and Swagger UI at `/docs`

## Layout

`src/models` (Beanie documents), `src/schemas` (request and response models), `src/repositories` (MongoDB access), `src/services` (validation and business rules), `src/v1/routes` (API), `src/utils` (JWT/role dependencies and the S3 client).

## Run and test

It starts with the rest of the stack from the repository root (`docker compose up --build`); see the [root README](../../README.md). Configuration comes from environment variables (`MONGO_URI`, `MONGO_DB`, `S3_*`, `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `APP_ENV`, `PORT`). The development placeholder internal token is accepted only with `APP_ENV=development`; otherwise the service refuses to start with it.

```bash
cd services/question-management-service
pip install -r requirements.txt pytest pytest-cov
pytest        # unit, JWT and MongoDB integration tests; fails below 80 % coverage
```
