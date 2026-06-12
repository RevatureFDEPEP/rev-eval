# feat(quiz-session): Quiz Session Creation — Backend (test-management-service)

## Summary
Implements the quiz session creation backend for `test-management-service`, covering the full stack from data model to API route with security guards and tests.

## Changes
- **Model:** `QuizSession` SQLAlchemy model with snapshot JSON, participant/test FK, status, timestamps
- **Repository:** CRUD layer for quiz sessions (create, get by ID, list by participant)
- **Service:** Business logic — validates test exists, enforces participant access, builds answer snapshot, applies submission cap (25 per test)
- **Route:** `POST /v1/api/sessions` — authenticated participant-only endpoint
- **Tests:** `test_quiz_session.py` covering happy path, duplicate cap, unauthorized access, and snapshot answer serialization guard

## Notes
- Correct answers retained in `snapshot_json` (server-authoritative, never serialized to client — enforced by `QuizQuestionOut` schema + regression test)
- Submission cap (25) is a coarse guard, not true rate limiting — adjustable via constant
- `create_all` explicit imports added for local reliability; Alembic migration still needed before prod schema evolution
- ⚠️ Gateway routing: `/v1/api/sessions` is not yet in `api-gateway-service/main.py` `ROUTES` — must be added before the endpoint is reachable through the gateway

## Checklist
- [x] Tests added
- [x] Ruff clean
- [x] No answers exposed in client-facing schemas
- [ ] Gateway route for `/v1/api/sessions` needs to be wired
