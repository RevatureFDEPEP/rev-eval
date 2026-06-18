# ADR 0002 — Scoring algorithm for multi-select questions

- **Status:** Accepted
- **Date:** 2026-06-18
- **Deciders:** Test-management / Scoring team

## Context

The scoring engine in test-management-service must score answers across question
types: single-answer (`mcq`, `true_false`, `single_select`), multi-select
(`multiple_select`, `multi_select`, `checkbox`), and free-text
(`short_answer`, `essay`, `fill_in_the_blank`). Scoring runs server-side inside
`SessionService.submit_answer`
([session_service.py:238-244](../../services/test-management-service/src/services/session_service.py#L238-L244))
and must be pure and deterministic (no DB, no side effects) so it is trivially
unit-testable and reusable.

Single-answer scoring is uncontroversial: normalize (case-fold + strip) and
compare for equality. The real decision is **how to score multi-select**, where
a participant may pick a subset, a superset, or a partially-overlapping set of
the correct options. Three scoring models were on the table:

- **Full-match (all-or-nothing):** 1.0 only if the selected set exactly equals
  the correct set; otherwise 0.0.
- **Jaccard similarity:** `|A ∩ B| / |A ∪ B|` — continuous partial credit that
  penalizes both misses and extra selections.
- **Set-overlap (recall):** fraction of correct options selected
  (`|A ∩ B| / |A|`), ignoring or lightly penalizing extras.

## Decision

**Multi-select questions are scored with full-match (all-or-nothing).** Jaccard
similarity *is* implemented, but it is **reserved for free-text question types**,
not multi-select.

Concretely:

- `exact_match.score_question` handles single-answer **and** multi-select. For
  multi-select it does set equality after normalization — every correct option
  present, no extras — yielding `score ∈ {0.0, 1.0}` and `is_correct = (score == 1.0)`.
  See [exact_match.py:42-56](../../services/test-management-service/src/scoring/exact_match.py#L42-L56).
- `partial_credit.score_question` implements Jaccard and is selected only when
  `question_type ∈ {"text", "short_answer", "essay", "fill_in_the_blank"}` via
  `_PARTIAL_CREDIT_TYPES` in
  [session_service.py:33-34](../../services/test-management-service/src/services/session_service.py#L33-L34).
- Both scorers return the same `ScoreResult` shape
  ([models.py](../../services/test-management-service/src/scoring/models.py)), so
  the caller picks a scorer by type and is otherwise agnostic.

## Alternatives considered

### Jaccard partial credit for multi-select
- ✅ Rewards near-misses; smoother score distribution; discourages
  "select everything" gaming because extras shrink the score.
- ❌ For a knowledge check, "knew 3 of 4 and guessed a wrong one" is pedagogically
  *not* a correct answer — partial credit blurs the pass/fail signal the
  trainer dashboard and reporting aggregates depend on.
- ❌ Harder to explain to participants ("why did I get 0.6?") and to trainers
  reconciling scores.
- Verdict: the right tool for **free-text**, where an exact string match is
  unreasonable, so we kept it — just pointed it at free-text only.

### Set-overlap / recall (`|A ∩ B| / |A|`)
- ✅ Simple, generous.
- ❌ Ignores extra (wrong) selections unless separately penalized, so selecting
  *all* options would score 1.0. Requires a second penalty term to be fair,
  which is just a worse-specified Jaccard. Rejected.

### Full-match for multi-select (**chosen**)
- ✅ Unambiguous and explainable: the answer is right or it isn't.
- ✅ Keeps `is_correct` a clean boolean that downstream aggregates
  (`AVG`/`MAX` in reporting per [ADR 0001](0001-cross-service-reporting-data-access.md))
  can rely on.
- ✅ Resistant to "select-all" gaming with zero extra logic.
- ⚠️ Coarse — a one-option miss scores the same as a blank answer. Accepted for
  a knowledge-check POC; a future per-question `scoring_policy` flag could let a
  trainer opt a specific multi-select question into Jaccard.

## Consequences

- Multi-select is strict: full marks require an exact set match. This is the
  behavior asserted in [test_scoring.py](../../services/test-management-service/tests/test_scoring.py).
- The scorer-selection rule lives in one place (`_PARTIAL_CREDIT_TYPES`); adding
  a new type or moving multi-select to partial credit is a one-line change.
- Unrecognized/missing question types fall back to single-answer exact match
  (defensive default in `exact_match`), so a bad `type` field never crashes
  scoring — it degrades to the strictest interpretation.
- If partial credit for multi-select is ever required, the engine already has a
  Jaccard implementation to point at — the decision is reversible at the
  type-routing layer without touching the scorers.
</content>
