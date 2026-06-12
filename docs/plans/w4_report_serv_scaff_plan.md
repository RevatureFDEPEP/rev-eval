# Week 4 — Reporting & Analytics Service Scaffold: Implementation Plan

**Branch:** `w4-report-serv-scaff`
**Date:** 2026-06-12
**Source of record:** repo re-analysis + `D:\_Revature\Week4\w4-report-serv-scaff\RevEval_Week4_Gap_Analysis_Temp.docx`

---

## 0. Re-analysis: confirm / refine the Week 4 gap analysis

The attached gap-analysis doc is **accurate about repo state** but ranks priorities for a
different branch than this one. Confirmations and refinements:

| Gap-analysis claim | Verdict | Refinement |
|---|---|---|
| W3 quiz/session slice is the top unimplemented item | **Confirmed for the program**, **out of scope here** | The quiz slice is being delivered on a separate branch / PR #107 (`w3-quiz-sec-slice`). This branch (`w4-report-serv-scaff`) is checked out on the pre-quiz baseline (`e4a3e55`) and its objective is the **reporting-and-analytics service scaffold** (Day 10 expectation). |
| `reporting-and-analytics-service` is empty; scaffold "after quiz data exists" | **Confirmed empty** (only a blank `README.md`); **refine the sequencing** | Reporting does **not** need to wait for the quiz slice. Rich score data already exists in `test_submissions` (`ai_score`, `trainer_score`, `final_score`, `status`) and `tests`. The scaffold can aggregate that today and automatically benefit from quiz-produced scores later. |
| Answer-key exposure / port-spoof risks | Confirmed, tracked on the quiz/security branch | Not re-fixed here, but the reporting service is designed to **inherit the same security posture** (gateway-only entry, role gating, loopback-only host port). |
| Reporting needs its own datastore / Alembic / compose service | Partially | For a **scaffold**, an own datastore is **deferred debt**, not required. We aggregate read-through over HTTP from `test-management-service`. The plan documents the future-store option as explicit deferred work. |

**Priority decision for this branch:** deliver a clean, tested, gateway-wired reporting
service scaffold that produces real analytics from existing submission data, mirroring the
established service architecture — rather than re-implementing the quiz slice.

---

## 1. Mental map of affected services

```
Browser (trainer/admin dashboards)
  → Next.js BFF (/api/v1/*)                         [frontend]
  → API Gateway (:8000)  — JWT verify + X-User-* inject
  → reporting-and-analytics-service (:8004)  ← NEW
        └─ httpx (Docker DNS, timeouts, correlation-id)
           → test-management-service (:8001)  /v1/api/submissions, /v1/api/tests
        (future) → question-management-service for item-level analytics
```

**Touched components**
- **NEW** `services/reporting-and-analytics-service/` — FastAPI service (mirrors test-management layout).
- **EDIT** `services/api-gateway-service/main.py` — add `^/v1/api/reports(/.*)?$` route + `SERVICE_PORTS` entry.
- **EDIT** `docker-compose.yml` — add the service (build, env, healthcheck, loopback port, `depends_on`).
- **EDIT** `.github/workflows/ci-pipeline.yml` — add `reporting-and-analytics-service` to the backend matrix.
- **(optional) EDIT** frontend `lib/api/` — a typed `reports` client + a trainer analytics view (gated behind a follow-up; see Order of Operations step 8).

No changes to existing service business logic, DB schema, or auth behavior.

---

## 2. Route contract (gateway path `/v1/api/reports`)

All endpoints are **read-only** and **trainer/admin-gated**.

| Method | Path | Purpose | Response (shape) |
|---|---|---|---|
| GET | `/health` | Liveness (no auth; direct) | `{ "status": "ok" }` |
| GET | `/v1/api/reports/overview` | Platform totals | `{ total_tests, total_submissions, by_status:{}, average_final_score, completion_rate }` |
| GET | `/v1/api/reports/tests/{test_id}` | Per-test analytics | `{ test_id, name, submission_count, by_status:{}, score:{min,max,avg,median,count}, completion_rate }` |
| GET | `/v1/api/reports/participants/{user_id}` | Per-participant analytics | `{ user_id, assigned, completed, average_final_score, tests:[{test_id,name,status,final_score}] }` |

- Gateway forwards `/v1/api/reports/*` → reporting service; JWT verified at gateway, `X-User-*` injected.
- Service requires `TRAINER`/`ADMIN` via a `get_current_trainer_or_admin` dependency (reuses the
  header-trust pattern from `test-management-service`).
- Upstream calls to `test-management-service` carry an `X-Correlation-Id` and a bounded timeout.

---

## 3. Data model

**Scaffold = no new database / no migrations.** The service is a **read-through aggregator**:
it fetches `test_submissions` and `tests` from `test-management-service` over HTTP and computes
statistics in memory in a pure `analytics/` module.

Rationale: avoids cross-service DB-schema coupling and an Alembic footprint in a scaffold; keeps
service boundaries clean; works against existing data immediately.

**Pydantic response schemas** (no ORM): `OverviewReport`, `TestReport`, `ParticipantReport`,
`ScoreStats`.

**Deferred (documented debt):** if reporting later needs historical snapshots, heavy aggregation,
or event-sourced analytics, add a dedicated datastore (`report_snapshots`) + Alembic + an ingestion
path. Out of scope for the scaffold; noted so it is a conscious decision, not an accident.

---

## 4. Security decisions

- **Gateway is the only public entry.** Host port published on **loopback only** (`127.0.0.1:8004:8004`),
  consistent with the hardening direction in the gap analysis.
- **Role gating.** Analytics is trainer/admin-only; participant tokens are rejected (403). The service
  trusts gateway-injected `X-User-*` (same model as `test-management-service`) — documented as a
  gateway-boundary trust assumption.
- **No answer keys, no secrets.** Reporting reads submissions/scores only — never question
  `correct_answers` and never `session_token`. Nothing sensitive is logged.
- **Resilient upstream calls.** Explicit `httpx` timeouts and graceful `503` on upstream failure so a
  reporting outage can never cascade into the core flow.

---

## 5. Test strategy

- **Pure analytics unit tests** (no I/O): parametrized tests for `ScoreStats` (min/max/avg/median,
  empty input, single value), status breakdown, completion rate. Highest value, fully deterministic.
- **Service tests with mocked HTTP**: `respx`/`monkeypatch` the `test-management` client; assert each
  endpoint maps upstream rows → report schema and handles upstream 5xx → `503`.
- **Role-guard tests**: participant role → 403; trainer/admin → 200.
- **Ruff** on the new service.
- **`docker compose config`** to validate the new service block.
- **Smoke test**: bring the service up (compose or uvicorn), `curl /health`, and one report endpoint
  through the gateway with a trainer token.
- **(after frontend wiring)** optional Playwright happy-path: trainer opens the analytics view.
- Coverage: keep the new service at/above the CI 70% gate (small surface + pure-function tests make
  this straightforward).

---

## 6. Order of operations

1. **Scaffold service skeleton** — `main.py`, `src/config/settings.py`, `src/logging_config.py`,
   `src/utils/dependencies.py` (role guard), `requirements.txt`, `Dockerfile`, `start.sh`, `pytest.ini`,
   `/health`. (Backend change → ask permission first.)
2. **Pure analytics module** + Pydantic schemas + unit tests (TDD-friendly, no I/O).
3. **Upstream client** (`httpx` to test-management) with timeouts + correlation id.
4. **Routes** (`overview`, `tests/{id}`, `participants/{id}`) + role guard + service tests.
5. **Gateway wiring** — `SERVICE_PORTS` + `ROUTES` entry; gateway route test if present.
6. **Compose** — add service (loopback port, env, healthcheck, `depends_on` test-management).
7. **CI** — add to backend matrix.
8. **(optional follow-up)** frontend typed `reports` client + minimal trainer analytics page;
   then lint/jest/tsc + Playwright smoke.
9. **Validate** — targeted pytest + ruff + `docker compose config` + smoke; capture commands/outputs.
10. **Report** — Word doc with mental map, files, results, blockers, risks, git/PR text.

---

## 7. Risks & deferred work

- **No own datastore** — analytics are computed live from `test-management-service`; fine for scaffold,
  but heavy/historical analytics will need a dedicated store + Alembic (deferred, documented).
- **Header trust** — inherits the gateway-boundary trust assumption; loopback-only port mitigates for
  local/demo. Downstream JWT verification is a program-wide hardening item tracked elsewhere.
- **Data richness** — until the quiz slice lands, per-question/skill analytics are limited to
  submission-level scores; endpoints are shaped to extend cleanly when richer data arrives.
- **CI image scan** — new service enters Trivy/Docker-build matrix; keep the base image current.

---

## 8. Acceptance criteria (this branch)

- Reporting service starts, exposes `/health`, and serves the three report endpoints through the gateway.
- Trainer/admin can fetch analytics; participants are rejected (403).
- Analytics computed from real submission data; no answer keys or secrets exposed/logged.
- Targeted backend tests + ruff pass; `docker compose config` valid; CI matrix includes the service.
- `git diff` scoped to the reporting service, gateway routing, compose, CI, and (optional) frontend client.
