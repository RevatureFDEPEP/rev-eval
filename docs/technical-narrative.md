# Technical narrative — two features worth talking about

Two features in `rev-eval-f5` carry the most interesting engineering decisions:
the **server-authoritative quiz session + scoring engine** in
test-management-service, and the **user reporting API** in
reporting-and-analytics-service. Each is told as what / why / how, tied to the
ADR that records the decision.

---

## Feature 1 — Server-authoritative sessions & the scoring engine

**What.** A participant starts a quiz (`POST /sessions/`) and submits answers
one at a time (`POST /sessions/{id}/answer`). The server samples the questions,
owns all timing, scores each answer as it arrives, and advances the attempt
until the last question flips the session to `SUBMITTED`. Scoring distinguishes
single-answer, multi-select, and free-text questions.

**Why these decisions.** Two things had to be true: the client must not be
trusted with timing or scoring, and *how* a multi-select answer earns marks had
to be a deliberate, defensible choice rather than an accident of whichever
formula got written first. A quiz where the browser computes the clock or the
score is a quiz you can cheat; and a multi-select scored with silent partial
credit produces a `score` that the trainer dashboard and reporting aggregates
can't interpret cleanly.

**How.** Timing is generated server-side (`server_now`, `expires_at`,
`session_token`) and persisted before the first response, so the client only
ever echoes state. Answer submission takes a `SELECT FOR UPDATE` lock and honors
an optional `Idempotency-Key` so a retried submission returns the cached result
instead of double-scoring. Scoring is two **pure** functions — `exact_match`
(full-match / all-or-nothing) and `partial_credit` (Jaccard) — selected by a
single `_PARTIAL_CREDIT_TYPES` set. **The concrete decision:** multi-select uses
**full-match**; Jaccard is reserved for free-text. That keeps `is_correct` a
clean boolean and resists "select-everything" gaming, while still giving
free-text the smooth credit it needs. This is recorded in
[ADR 0002 — Scoring algorithm for multi-select questions](adr/0002-multi-select-scoring-algorithm.md),
which also captures the rejected alternatives (Jaccard-for-everything,
set-overlap/recall) and why full-match won.

---

## Feature 2 — The user reporting API

**What.** Two endpoints over a participant's attempt history: a summary
envelope (`GET /reports/user/{id}` — total attempts, average/best score, total
time, most recent attempt) and a paginated, filtered, sorted attempt list
(`GET /reports/user/{id}/attempts`).

**Why these decisions.** The authoritative attempt data is *owned by another
service* (test-management). The interesting question wasn't how to compute an
average — it was **where the data should live** so reporting can aggregate it
without becoming hostage to another service's schema or uptime. Reporting is
read-heavy and latency-sensitive; pulling a full attempt history over HTTP and
averaging it in Python on every request, or reaching straight into another
service's tables, are both traps that look fine at 50 users and fall over later.

**How.** Reporting owns a denormalized `session_mirror` table in its own schema,
fed by an event projection from test-management; reporting reads only its own
table. That turns every report into plain local SQL — the summary is computed in
**one query** (`count`/`avg`/`sum`/`max` plus a scalar subquery for the most
recent attempt), and the list endpoint is paged with a bounded page size (≤100),
filtered, and sorted against indexes the reporting team controls. The **concrete
decision** — event projection over synchronous API calls or direct cross-service
DB reads — is recorded in
[ADR 0001 — Cross-service data access for the reporting service](adr/0001-cross-service-reporting-data-access.md),
including the eventual-consistency trade-off we accepted and the
not-yet-built projection writer tracked as follow-up.

---

**Common thread.** Both features push authority to where it belongs — the server
owns scoring and timing; the reporting service owns its own read-optimized copy
of the data it serves. In both cases the *mechanism* was straightforward; the
value is in the decision, which is why each is anchored to an ADR rather than
left implicit in the code.
</content>
