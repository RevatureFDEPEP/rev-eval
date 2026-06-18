# AI involvement & verbal-defence prep

## How AI was used

This codebase was built with AI assistance (Claude Code) under a
human-in-the-loop workflow: every feature started from a written spec, the AI
proposed a step-by-step plan, a human approved it before any multi-file edit, and
every backend change was verified by a live `docker compose` gateway round-trip —
not just unit tests — before commit. The AI located code, drafted
implementations, and wrote tests; the human made the design decisions, chose
between alternatives (recorded in the ADRs), and signed off on each plan.

**Why involvement is tracked here, not as a per-line comment.** Effectively
every line is AI-assisted, so `# AI-authored` markers would be noise that
obscures rather than informs. Instead, authorship and decision provenance live
in two durable places: the ADRs (`docs/adr/`) capture *who decided what and why*,
and this document captures *how to defend it*. Inline comments are reserved for
explaining non-obvious logic (e.g. the Jaccard rationale in
`partial_credit.py`, the gateway `X-User-Role` overwrite invariant), regardless
of author.

## Verbal-defence prep — questions to expect

**Scoring (W3-F2 / [ADR 0002](adr/0002-multi-select-scoring-algorithm.md))**
- *Why Jaccard over exact-match for MULTI?* Exact-match scores 3-of-4-correct
  the same as a blank — it discards partial knowledge. Jaccard awards it
  proportionally.
- *Why not recall (`∩ / correct`)?* Recall ignores wrong picks, so "select
  everything" scores 1.0 — gameable. Jaccard's union denominator penalises wrong
  picks.
- *What happens to a TEXT question?* The engine raises `ValueError`; the answer
  endpoint records a `manual_grading_required` zero and advances the session so
  it can't wedge. (Known limitation — technical-debt item 6.)
- *Are the scorers tested?* Yes, hermetically — they're pure functions, so the
  full type × outcome matrix runs without a DB.

**Reporting (W4-F1 / [ADR 0001](adr/0001-reporting-cross-service-data-access.md))**
- *Why read test-management's database directly instead of HTTP or events?*
  Lowest effort, always-fresh reads, adequate at this scale; HTTP adds endpoints
  + latency, event-projection adds a sync pipeline that doesn't exist (no message
  bus). Both alternatives documented and rejected as premature.
- *If you don't own tables, why a second Postgres?* Two Alembic chains can't
  share one `alembic_version` row. The reporting Postgres isolates its migration
  lifecycle; `0001_baseline` is an empty no-op head that just makes
  `alembic upgrade head` a valid bootstrap.
- *What's the risk?* Schema coupling — a column rename upstream breaks reporting
  at query time. Mitigation is integration tests, which aren't built yet
  (technical-debt items 1 + 8). This is the honest weak point.

**Security**
- *Can a candidate pull the answer key?* No. Answer-bearing reads are gated to
  TRAINER; internal scoring uses gateway-bypassing direct calls that set
  `X-User-Role: TRAINER`. Safe because the gateway *overwrites* that header from
  the verified JWT, so a browser can't forge it. The invariant is the security
  boundary — defended in technical-debt item 9.

## Honest limitations to volunteer

Don't wait to be asked: no integration tests (item 1), TEXT auto-scoring is a
stub (item 6), reporting↔test-management schema coupling is unguarded (item 8).
These are the three that would matter first in production.
