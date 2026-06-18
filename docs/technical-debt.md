# Technical Debt Inventory

**Last audited:** 2026-06-15 (W4-F5, Day 20 capstone)
**Scope:** the `rev-eval` platform as it stands after W4-F4 — the full vertical
slice from candidate login → session scoring → trainer aggregate reporting.

This is an **audit, not a repayment**. Each item below records *what* the
shortcut is, *where* it lives, the *condition under which it bites*, and an
*urgency* rating relative to the platform's **current scale**: local-first,
single-node Docker Compose, demo/seed data, no production traffic. An item that
is "fine now" is not a non-issue — it is a clock that starts when the platform
leaves the laptop. Several shortcuts here are *intentional* candidate-task
boundaries (the repo is a teaching substrate); those are flagged as such.

Urgency key — judged against current scale:

| Urgency | Meaning |
|---|---|
| **high** | Already a liability the moment the platform leaves local dev (security or correctness). |
| **med** | Safe at demo scale; degrades or risks drift as data/usage grows. |
| **low** | Cosmetic, contained, or only reachable in stale local state. |

---

## 1. Hardcoded magic values & weak security defaults

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| Default `JWT_SECRET = "change-me-in-production"` | `services/user-service/src/config/settings.py:21`, `services/reporting-and-analytics-service/src/config/settings.py:25`, `.env.example` | The secret is env-overridable, but if a non-local deploy ships without setting it, every JWT is forgeable — anyone can mint a TRAINER token. The user-service *issues* with it and reporting *verifies* with it, so they must also stay in sync. | **high** |
| CORS `allow_origins = ["*"]` default | `services/user-service/src/config/settings.py:14` & `main.py:24-28`; `services/reporting-and-analytics-service/src/config/settings.py:33`; `services/question-management-service/src/config/settings.py:25`; test-management-service `main.py` | Wildcard CORS is fine behind the gateway in local dev; on a public origin it lets any site make credentialed cross-origin calls. Default should be closed, opened per-env. | **high** |
| Default MinIO creds `minioadmin`/`minioadmin` | `services/question-management-service/src/config/settings.py:38-39` | Env-overridable, but the default is well-known; an exposed MinIO with defaults is fully readable/writable. | med |
| Repeated page-size magic numbers (`100`/`500`/`20`) | `question_routes.py` (filter endpoints), `user_route.py:49` (`100`/`1000`) | No central pagination config; limits drift between endpoints and are easy to mistune. Pure maintainability. | low |
| Presign expiry magic `3600` | `services/question-management-service/src/config/settings.py` (`S3_PRESIGN_EXPIRY_SECONDS`) | Hardcoded 1h URL lifetime; not tunable per use case. | low |

## 2. Unpaginated list endpoints (return-all-rows)

Condition (all rows below): fine against seeded demo data; response size and
DB scan grow O(n) with rows, so payloads bloat and latency climbs as the table
fills. The W4 reporting endpoints (`/reports/user/{id}/attempts`) already model
the intended `page`/`size`/`total` envelope — these predate that pattern.

| Endpoint | Location | Urgency |
|---|---|---|
| `GET /tests/`, `/tests/created-by/{uid}`, `/tests/submissions-by/{uid}` | `services/test-management-service/src/v1/routes/test_route.py` | med |
| `GET /categories/`, `/categories/{id}/skills` | `.../routes/category_route.py` | med |
| `GET /skills/` | `.../routes/skill_route.py` | med |
| `GET /submissions/` + 4 trainer/graded list variants | `.../routes/test_submission_route.py` | med |
| `GET /questions/` (get_all_questions) | `services/question-management-service/src/v1/routes/question_routes.py` | med |

## 3. Missing input validation

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| Raw-string path/query params (no enum): `by-type`, `by-skill`, `by-difficulty`, `filter` | `services/question-management-service/src/v1/routes/question_routes.py` | Unvalidated strings reach the query layer; a typo silently returns empty rather than 422, and the surface is wider than the documented value set. | med |
| Presigned `content_type` not enforced in signature | `question_routes.py` (`/questions/presigned-upload-url`) | Docstring says `image/png`/`image/jpeg` but nothing rejects other types at the boundary. | low |

## 4. Schema not under migration control

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| user-service uses `Base.metadata.create_all` | `services/user-service/src/db/session.py` | No version history / rollback for schema; drift between environments is invisible and unreproducible. Only test-management-service is Alembic-owned. | med |
| question-management-service: implicit Beanie/ODM schema | `services/question-management-service/src/db/session.py` | Mongo is schemaless by nature, but field shape changes (e.g. the W2-F6 vs. legacy question shapes) have no recorded migration — see §6. | med |
| reporting-and-analytics-service Alembic baseline `0001` is empty | `services/reporting-and-analytics-service/alembic/versions/` | Intentional (ADR 0001: reporting owns no tables, reads TMS directly). Listed for completeness — *not* debt, a recorded decision. | low |

## 5. Mocks where integration would help / thin test coverage

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| Services with no `tests/` dir (user-service, parts of question-service) | per-service `services/<svc>/` | CI skips coverage where no suite exists; regressions land silently. Adding suites is an explicit candidate task. | med |
| Idempotency replay not body-fingerprinted | test-management-service `IdempotencyRepository` (W3-F7 item 9) | A retry with the *same* `Idempotency-Key` but a *different* body replays the original response — masks a client bug rather than 409-ing it. | med |
| QMS question fetch runs while holding `SELECT FOR UPDATE` | test-management-service `session_service.submit_answer` (W3-F7 item 9) | The row lock is held across an outbound httpx call; a slow QMS lengthens lock hold time and serializes concurrent answerers more than necessary. | med |

## 6. Auth boundary — downstream header trust

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| Downstream services trust `X-User-Id/Email/Role` without re-verifying the JWT | gateway injects at `services/api-gateway-service/main.py`; consumed by test-management, user, question services | The gateway is the sole auth boundary. If any service is reachable directly (misconfigured network, port exposed), spoofed `X-User-Role: TRAINER` headers are trusted. The reporting service is the lone exception — it re-verifies the JWT itself (W4-F3 defense-in-depth), the pattern the others should adopt. | med |

## 7. Legacy data-shape rendering

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| ✅ **CLOSED (W5-F3)** — Option-less `true_false` docs rendered "Error: No options available" | `frontend/src/components/take/SingleSelectQuestion.tsx:30-31` | **Correction:** option-less is the *canonical* `true_false` shape, not a legacy artifact — W2-F6 authoring stores `correct_answers: [bool]` with no `options` (`frontend/src/components/trainer/question-form-utils.ts:223-226`), so *every* true/false question hit this, not just stale volumes. Fixed by a dedicated `TrueFalseQuestion` widget in `components/take/` (True→`[1]`/False→`[0]`; scores via exact-match bool↔int set-equality, no backend change). See [W5-F3](features/w5-f3-legacy-true-false-rendering.md). **Note:** seed `seed_rag_context_questions.py` has a self-contradictory doc (`correct_answers: [0]` with explanation "True", line 48) — a seed data defect deferred to a separate data/seed fix (not a render bug; full shape migration is §4). | ~~low~~ closed |

## 8. Cruft & stale artifacts

| Item | Location | Condition under which it matters | Urgency |
|---|---|---|---|
| TODO: timezone-naive timestamps "for POC" | `services/test-management-service/src/schemas/test_submission_schema.py:30` | Naive datetimes invite off-by-TZ bugs once clients span zones. | low |
| Checked-in `dev.db` SQLite | `services/test-management-service/dev.db` | Local-experiment artifact in version control; deployed config is Postgres. Should be git-ignored/removed. | low |
| Stale `start.sh` / `test-services.sh` | repo root | Reference nonexistent services (Consul, WorkOS, notification/AI/lambda); `docker-compose.yml` is authoritative. Misleads new readers. | low |

---

## Prioritized repayment backlog

Ordered most- to least-urgent against current scale. Each is a *future*
feature; none is repaid in W4-F5.

1. **Close the security defaults** — fail fast (no default) on `JWT_SECRET` for
   any non-local profile; default CORS to closed and open per-env. (§1, high)
2. **Rotate/parameterize MinIO creds** off the shipped default. (§1, med)
3. **Bring user-service under Alembic** (and define a question-doc shape
   migration story). (§4, med)
4. **Paginate the list endpoints** using the W4 `page/size/total` envelope.
   (§2, med)
5. **Harden the auth boundary** — extend the reporting-service JWT re-verify
   pattern to the other downstream services, or lock down direct reachability.
   (§6, med)
6. **Fingerprint idempotency bodies; shorten the lock window** (fetch the
   question before taking `FOR UPDATE`). (§5, med)
7. **Enum-validate the question filter params.** (§3, med)
8. **Remove cruft** — `dev.db`, stale scripts, POC TODO. (§8, low)
9. **Normalize/handle legacy `true_false` docs** or add a dedicated widget.
   (§7, low)
