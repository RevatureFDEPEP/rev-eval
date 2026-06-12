# ADR 0001 — Reporting reads test-management's Postgres directly (shared-DB)

- **Status:** Accepted
- **Date:** 2026-06-12
- **Feature:** W4-F1 (Candidate Results Reporting Endpoints)
- **Deciders:** Richard Hawkins

## Context

`reporting-and-analytics-service` (W2-M10 scaffold) must serve read-heavy
aggregate endpoints over quiz-attempt data: a per-user summary envelope and a
paginated attempt history now (W4-F1), and trainer-facing GROUP BY / HAVING /
window-function aggregates next (W4-F3).

The authoritative attempt data lives in **test-management-service's** Postgres
(`eval_ai_dev`): the `sessions` table (one row per attempt: `status`,
`server_now` start anchor, `submitted_at`) and the `answers` table (one scored
row per question slot, `score` ∈ [0, 1]). The reporting service was scaffolded
with its **own** Postgres (`eval_ai_reporting`, empty Alembic `0001` baseline)
— the two-database topology the spec prescribes — so the data the reports need
is, by construction, in a database the service does not own.

A second forcing fact (found in W3-F6): session finalize never writes the
legacy `test_submissions` table. The sessions/answers slice and the seeded
submissions are parallel systems, so a just-taken quiz shows a score **nowhere**
in the product. Whatever pattern reporting adopts is also the answer to "how do
scores become user-visible".

## Decision

Reporting reads `sessions`, `answers`, and `tests` **directly from
test-management-service's Postgres** via a second, read-only async engine
(`TMS_DB_*` settings → `tms_engine` / `get_tms_db()`), alongside its existing
engine for `eval_ai_reporting`.

Containment rules for the coupling this creates:

1. All mapped copies of TMS tables live in **one module**,
   `src/models/tms_readonly.py`, on their own `TmsBase` metadata — declared
   read-only, schema owned by the TMS Alembic chain.
2. `TmsBase` is **never** wired into reporting's Alembic `target_metadata`;
   autogenerate cannot emit DDL for tables this service doesn't own.
3. The reporting service performs **no writes** on the TMS engine; only
   `SELECT`s built in `report_repository.py`.
4. Unit tests pin the column contract, so an upstream TMS schema change that
   breaks reporting fails loudly in CI rather than silently at runtime.

**Consequence for the W4-F1 "migration" step:** reporting needs **no tables of
its own** for this feature. Alembic `0001_baseline` remains head, and the
migration the spec asks to "generate for any reporting-side tables" is empty by
decision, not by omission.

Scores become user-visible through these read endpoints (consumed by W4-F2's
results page) — not by bridging finalize into `test_submissions` and not via a
reporting-side mirror.

## Alternatives considered

### HTTP calls to test-management-service
Reporting would call TMS endpoints and aggregate in Python. Rejected:

- TMS exposes no bulk read endpoints; each report would need new TMS API
  surface, putting reporting's query needs on another service's roadmap.
- Aggregation moves from SQL (where the data is) into app code — exactly what
  the spec rules out ("no client-side re-aggregation").
- W4-F3's GROUP BY / HAVING / `percentile_cont` window queries over the full
  sessions+answers tables are impractical over paginated HTTP without bulk
  data transfer on every request.

### Event projection / sessions-mirror table in `eval_ai_reporting`
TMS would emit events (or reporting would poll) to maintain a local mirror,
migrated via reporting's Alembic. Rejected for now:

- No message bus exists in the compose stack; building one (or a poller) is
  well beyond Day-16 scope.
- Dual-write/sync introduces lag and failure modes (missed events, replay,
  backfill) with zero benefit at local-first scale.
- It is, however, the natural **evolution path**: if reporting load ever
  threatens the operational database, this ADR is superseded by a projection
  with its own store — the repository layer is the seam where that swap
  happens.

### Bridging finalize → `test_submissions`
Make TMS's finalize write the legacy submissions row, and report from there.
Rejected: it couples the scoring write path to a half-parallel legacy schema,
duplicates per-attempt truth in two tables of the same database, and still
leaves reporting reading a TMS-owned table — all of the coupling, plus a new
write path to keep consistent.

## Consequences

- **Positive:** zero sync lag (reports reflect a submit immediately); aggregates
  run as single SQL round trips with `func.avg/count/sum` and subqueries;
  W4-F3's window-function queries get a straight path; no new infrastructure.
- **Negative (accepted):** reporting deploys break if TMS renames/retypes the
  columns it reads — mitigated by the containment rules above; the two services
  must share network reachability to `postgres` (already true in compose); the
  read load lands on the operational DB (acceptable at this scale, revisit per
  the projection path above).
- `docker-compose.yml` now gives reporting `TMS_DB_*` env and a
  `depends_on: postgres: service_healthy` edge.
