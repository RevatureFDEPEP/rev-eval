# W3-F1 — Quiz Session Creation Backend

**Status:** ❌ Not Started
**Spec:** `days_11_15_features.md` §1 (Day 11)
**Depends on:** [W2-F7](w2-f7-alembic-category-domain.md) (sessions table is a new Alembic revision on test-management-service's schema), W2 Compose topology (question-management-service + Mongo must be healthy for the cross-service httpx call), [W2-F5](w2-f5-minio-presigned-uploads.md) (question bank must be seeded so `$sample` returns results)
**Unblocks:** W3-F2 (Scoring Engine — needs sessions table + `current_index` to lock and advance), W3-F3 (Frontend Skeleton — page calls `POST /sessions` server-side on load)
**Last updated:** 2026-06-12

`POST /sessions` endpoint in test-management-service that samples questions
from question-management-service and creates a quiz session.

## Steps

- [ ] **1. Sessions table + migration** — `QuizSession` SQLAlchemy model;
      Alembic revision `0004_add_quiz_sessions.py` (after W2-F7's `0003`).
- [ ] **2. POST /sessions handler** — creates session, sets `current_index=0`,
      returns session contract.
- [ ] **3. Cross-service question fetch** — httpx call from test-management to
      question-management `GET /v1/questions/sample?test_id=` for the question
      list.
- [ ] **4. Correlation-id propagation** — forward `X-Correlation-Id` on the
      httpx call.
- [ ] **5. Response contract** — `SessionRead` schema with all fields the
      frontend needs.
- [ ] **6. Gateway route** — expose `POST /v1/sessions` through the API gateway.

## Evidence

None on `tianyac` branch. No `QuizSession` model, no Alembic env, no session
endpoints in test-management-service.

Note: another contributor delivered this feature on branch
`richardh-feat-W3F1`; that work is not yet merged into `tianyac`.

## Remaining

All steps. Blocked on [W2-F7](w2-f7-alembic-category-domain.md).
