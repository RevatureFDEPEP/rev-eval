# Technical Narrative — rev-eval

A one-page what/why/how for the two most interesting features in the build,
each tied to a concrete decision and the ADR that records it. Companion to the
[technical-debt inventory](technical-debt.md).

## Feature 1 — The pure scoring engine

**What.** `score_question(question_type, correct_answers, submitted_answers)`
turns a candidate's selection into a score in `[0.0, 1.0]`. Single-select
(`mcq`/`true_false`) is exact-match all-or-nothing; multi-select uses the
**Jaccard index** for partial credit.

**Why this shape.** The engine is a *pure* function — no DB, no clock, no httpx,
no global state. That was a deliberate decision: scoring is the part most worth
being certain about, and purity makes it exhaustively unit-testable with plain
`pytest` (no async runner, no live datastore) and cheap to reason about. The
route layer fetches the answer key over HTTP and feeds it in; the engine never
touches the network. The partial-credit algorithm choice — full-match vs.
Jaccard vs. set-overlap — is the consequential one, recorded in
[ADR-0002](adr/0002-multi-select-scoring-algorithm.md). Jaccard won for being
symmetric (missing a right answer and adding a wrong one cost the same),
anti-gaming (selecting everything collapses the score toward `|A|/|options|`),
and explainable as a single ratio.

**How it shows up in the code.** `src/scoring/engine.py` normalizes both answer
lists to a `frozenset` at the boundary (order/duplicates can't affect the
score), then branches per type. The "select-all gaming" property and the
degenerate empty/empty case each have a dedicated regression test, and the
1-indexed `option_id` encoding contract is pinned in `AnswerSubmit` and the
engine docstring so the frontend submit path can't silently score `0.0`.

## Feature 2 — Server-authoritative answer submission

**What.** `POST /test-sessions/{id}/answer` scores one answer and advances the
session, with the server — never the client — owning the clock, the cursor, and
the answer key.

**Why this shape.** A quiz that trusts the client is a quiz that can be cheated.
The decision was **server-authoritative state everywhere**: the candidate
identity comes from the gateway-verified claim (never the body), the
correct-answer key is fetched server-side and never returned, expiry is checked
against a server clock on every mutation, and a candidate may only answer the
question at the server's current cursor. The same posture is why `submitted_at`
is stamped from the server clock on the submit transition (so W4-F1 reporting can
sort on it) rather than accepting a client timestamp.

**How it shows up in the code.** The endpoint combines three concurrency
defenses so a duplicate submission resolves to a correct `200`, not a `500` or a
double-score: a `SELECT … FOR UPDATE` row lock, a `(session_id, idempotency_key)`
unique constraint, and an `IntegrityError` re-read that returns the winning row.
Idempotency replay returns the prior result without re-scoring. The remaining
weak point — the *session-creation* guard is check-then-act and not race-proof —
is logged honestly in the [debt inventory](technical-debt.md) (#4) with the fix
(a partial-unique index) named.

## A forward decision — reporting's data access

The reporting service is scaffold-only, but its cross-service data-access
pattern is already decided and recorded in
[ADR-0001](adr/0001-cross-service-data-access-for-reporting.md): a **sessions
mirror table** in the reporting service rather than a direct shared-DB read or
HTTP aggregation. The reasoning — relational aggregates want a local table, and
a versioned projection keeps the service boundary intact — is the kind of choice
worth writing down before code locks it in.

## AI-assisted development and review

Parts of this codebase were drafted with AI assistance (Claude Code). The
working posture, defensible on review:

- AI was used to draft route scaffolding, test suites, docstrings, and these
  ADRs; every change went through human review before commit and through the
  same PR review gate as hand-written code (see the review threads on PRs
  #149 and #151).
- Two AI-drafted bugs were caught and fixed in exactly that review loop — a
  merge that dropped the `AnswerResult`/`AnswerSubmit` imports and one that
  dropped the `score_question` import, both of which broke at import time and
  were surfaced by running the suite, not by trusting the diff.
- The scoring algorithm and the cross-service pattern were **not** delegated as
  black boxes: the trade-offs were enumerated (ADR-0001, ADR-0002) and the chosen
  option is defensible against its alternatives, which is the point of recording
  them.
