# Technical Narrative — Two Features Worth Telling

**Last updated:** 2026-06-15 (W4-F5, Day 20)

Two features carried the most interesting decisions of the four weeks. Each is
told as **what / why / how**, tied to the ADR that records its decision.

---

## 1. Reporting cross-service data access (W4-F1) — ADR [0001](adr/0001-reporting-cross-service-data-access.md)

**What.** A read-heavy `reporting-and-analytics-service` that serves the
candidate results page and the trainer dashboard: a per-user summary envelope,
a paginated attempt history, and trainer-only GROUP BY / window-function
aggregates over every attempt.

**Why.** Two forcing facts collided. First, the service was scaffolded (W2-M10)
with its *own* Postgres (`eval_ai_reporting`) — the spec's two-DB topology — but
the authoritative attempt data (`sessions`, `answers`) lives in
test-management-service's `eval_ai_dev`. The data the reports need was, by
construction, in a database this service does not own. Second (surfaced in
W3-F6): session finalize never writes the legacy `test_submissions` table, so a
just-taken quiz showed a score *nowhere* in the product. Whatever pattern
reporting adopted was also the answer to "how do scores become visible at all."

**How.** Reporting reads `sessions`/`answers`/`tests` **directly** from TMS
Postgres over a second, read-only async engine (`tms_engine` / `get_tms_db()` in
`src/db/session.py`), chosen over HTTP calls (no bulk read surface; would push
aggregation into Python) and event projection (no message bus exists; well
beyond Day-16 scope). The coupling is *contained*, not hidden: TMS table copies
live in one module on their own `TmsBase` metadata, are never wired into
reporting's Alembic `target_metadata`, are SELECT-only, and unit tests pin the
column contract so an upstream schema change fails loudly in CI. The repository
layer is the explicit seam where a future projection-with-its-own-store would
swap in — the documented evolution path if read load ever threatens the
operational DB. ADR 0001 records the rejected alternatives and the accepted
negatives.

---

## 2. Scoring engine + attempt locking (W3-F2) — ADR [0002](adr/0002-multiselect-scoring-algorithm.md)

**What.** Deterministic scoring for single-select (exact-match) and
multi-select (partial-credit) questions, wired into a `POST /sessions/{id}/answer`
endpoint that locks the attempt, is idempotent, and finalizes the session state
machine.

**Why.** Two correctness problems. (1) Multi-select needs a *fair* partial score
— a candidate who picks 3 of 4 correct options should beat one who picks none,
without "select everything" gaming a high score. (2) A candidate who
double-submits (network retry, double-click) must not double-advance or
double-score the attempt.

**How.** Scoring is a set of **pure functions** (`src/scoring/`, no DB/network)
so the bulk of coverage needs no fixtures. Multi-select uses the **Jaccard
index** `|correct ∩ submitted| / |correct ∪ submitted|` — bounded, symmetric
(missed-correct and spurious-wrong penalized equally), chosen over all-or-nothing
(discards partial knowledge) and correct-minus-wrong (asymmetric,
under-penalizes spurious picks); ADR 0002 has the full argument. Concurrency is
handled with a **pessimistic lock**: the service issues `SELECT ... FOR UPDATE`
on the session row *before* reading `current_index`, so concurrent retries
serialize. A **required `Idempotency-Key`** dedups retries (the stored response
replays without re-scoring), and the **state machine** advances `current_index`,
flips `status → SUBMITTED` on the last question, and returns 409 on any further
mutation or an elapsed deadline. The real-Postgres concurrency proof (one 200 +
one 409, index advanced exactly once) was added in W3-F5.

---

*The `docs/FEATURE_STATUS.md` tracker and the per-feature detail docs under
`docs/features/` carry the what/why/how for the remaining features.*
