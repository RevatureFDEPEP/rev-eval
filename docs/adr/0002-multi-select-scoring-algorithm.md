# ADR 0002 — Multi-select scoring algorithm

- **Status**: Accepted
- **Date**: 2026-06-18
- **Feature**: W3-F2 (Scoring engine + answer endpoint)

## Context

The scoring engine grades a submitted answer against a question's correct-answer
key (`services/test-management-service/src/scoring/`). Single-select questions
(MCQ, TRUE_FALSE) are unambiguous: the submission either equals the key or it
does not. Multi-select (MULTI) questions are not — a candidate can pick some of
the correct options, all of them, or some correct plus some wrong. A scheme that
only awards credit for an exact match throws away the signal in a near-miss; a
scheme that is too generous rewards "select everything."

Answers are normalised to **order-insensitive, duplicate-collapsed sets** of
1-indexed option positions (`exact_match._to_set`), so the choice is really
"what set-comparison metric scores a MULTI submission."

Three metrics were considered for MULTI:

1. **Exact full-match** — `1.0` iff `submitted == correct`, else `0.0`.
2. **Jaccard index** — `|correct ∩ submitted| / |correct ∪ submitted|`.
3. **Set-overlap / recall** — `|correct ∩ submitted| / |correct|`.

## Decision

**Jaccard index for MULTI; exact-match for everything else.**
`partial_credit.score_question` delegates single-select and TRUE_FALSE straight
to `exact_match` (partial credit is undefined there), and for MULTI returns
`len(correct & submitted) / len(correct | submitted)` with `is_correct` reported
as the strict `correct == submitted`. Both modules are pure (no I/O, no
mutation) and return a `ScoreResult(is_correct, score, max_score, algorithm)`.

Types the engine cannot key-score (TEXT) raise `ValueError`; the answer endpoint
catches it and records a `manual_grading_required` zero so the session still
advances rather than wedging (see [technical-debt.md](../technical-debt.md)).

Edge case: empty correct-key **and** empty submission is vacuously `1.0`.

## Consequences

**Positive**
- Rewards partial knowledge proportionally and symmetrically: missing a correct
  option and adding a wrong option both shrink the score, because the union (the
  denominator) grows for wrong picks while the intersection (the numerator) does
  not. "Select everything" is penalised — it inflates the union.
- One metric, one code path: MCQ/TRUE_FALSE reuse exact-match as the degenerate
  two-outcome case, so there is no separate single-select scorer to keep in sync.
- Pure functions → exhaustively unit-testable without a DB (the scoring test
  matrix runs hermetically).

**Negative**
- Jaccard weights a wrong pick and a missed pick equally. A question author who
  wants asymmetric penalties (e.g. "wrong selection hurts more than an omission")
  cannot express that today. Revisit if exam policy demands weighted penalties.
- The score is not linear in "fraction correct" — partial scores depend on key
  size, which can surprise candidates comparing two MULTI questions. Documented
  rather than hidden.

## Alternatives considered

- **Exact full-match for MULTI** — simplest and unambiguous, but binary: a
  4-option question with 3 of 4 correct scores the same `0.0` as a blank answer.
  Discards real partial knowledge. Rejected; it is what `exact_match` already
  provides for single-select, where the all-or-nothing semantics are correct.
- **Set-overlap / recall (`∩ / correct`)** — counts how much of the key was
  found but **ignores wrong picks entirely**: selecting all options scores a
  perfect `1.0`. That is a gameable scoring function. Rejected. Jaccard is the
  recall metric's denominator-penalised cousin and closes exactly this hole.
