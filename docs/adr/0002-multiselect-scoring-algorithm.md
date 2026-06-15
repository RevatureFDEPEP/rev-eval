# ADR 0002 — Multi-select questions scored by the Jaccard index

- **Status:** Accepted
- **Date:** 2026-06-08
- **Feature:** W3-F2 (Scoring Engine + Attempt Locking)
- **Deciders:** Richard Hawkins

> The canonical, in-code statement of this decision is the module docstring of
> `services/test-management-service/src/scoring/partial_credit.py` (captured
> deliberately during W3-F2 step 1). This ADR lifts that rationale into the
> standard structure for the W4-F5 audit.

## Context

The quiz engine scores three question types. Single-select questions (`mcq`,
`true_false`) are scored by **exact set equality** in
`src/scoring/exact_match.py`: the submitted set must equal the correct set, else
`0.0` — there is exactly one right answer, so partial credit is meaningless.

**Multi-select (`multi`) is the open decision.** A candidate may select some of
the correct options, miss others, and add spurious wrong ones. We need a single
scalar in `[0, 1]` that:

- rewards partial knowledge (3-of-4 correct should beat 0-of-4),
- penalizes over-selection (clicking every option must not game a high score),
- is order-independent and deterministic,
- and is a **pure function** — no DB, no network, no side effects — so the bulk
  of scoring coverage needs no fixtures (W3-F2 step 5). The answer endpoint
  calls it through the `src/scoring` dispatch and never hands it DB rows.

`is_correct` (distinct from the fractional `score`) is reserved for a perfect
answer, used by the state machine; partial overlap yields a fractional `score`
with `is_correct = False`.

## Decision

Score `multi` answers by the **Jaccard index** of the correct and submitted
option sets:

```
score = |correct ∩ submitted| / |correct ∪ submitted|
```

- Range `[0, 1]`; `1.0` iff the sets are equal (→ `is_correct = True`).
- A degenerate question with no correct answers scores `0.0`.
- Implemented in `src/scoring/partial_credit.py::score_question`, dispatched by
  type from `src/scoring/__init__.py`; `ScoreResult` is the shared return shape
  (`src/scoring/result.py`).

The defining property is **symmetry**: a missed-correct option and a spurious-
wrong option are penalized the *same way* — each enlarges the union without
adding to the intersection. Selecting everything is therefore self-limiting:
the score floors at `|correct| / |all options|`, never near `1.0`.

## Alternatives considered

### All-or-nothing (`1.0` iff sets match, else `0.0`)
Rejected: discards every signal of partial knowledge. A candidate who picks
3 of 4 correct options scores the same `0.0` as one who picks none — useless for
the difficulty/distribution analytics W4-F3 builds on the `answers` table.

### Correct-minus-wrong (`(hits − misses) / |correct|`, floored at 0)
Graded, but **asymmetric and ill-conditioned**: it is unbounded below before the
floor, and it divides by `|correct|` while ignoring the size of the *union*, so
spurious wrong picks are under-penalized relative to missed-correct ones. Two
candidates with genuinely different answer quality can collide on the same score.

### Jaccard (chosen)
Bounded, order-independent, symmetric, one line of set arithmetic, trivially
unit-tested across the full exact/partial matrix. The one accepted quirk — a
non-zero floor for "select everything" — is acceptable and is exactly the
over-selection the symmetry argument keeps small.

## Consequences

- **Positive:** trivial to test (pure function, 100% covered in
  `tests/test_scoring.py`); aggregation-friendly (`answers.score ∈ [0,1]`
  averages cleanly for W4-F1/W4-F3 reports); no special cases beyond the empty
  correct-set guard.
- **Negative (accepted):** "select all options" yields a small positive score
  rather than `0.0`; if an exam ever needs to punish over-selection harder, the
  pure-function seam makes swapping in a penalized variant a localized change.
- **Out of scope:** free-text (`text`) questions are recorded with score `0.0`
  awaiting manual grading (noted in W3-F2 Remaining) — not a scoring-algorithm
  decision.

## Related

- ADR [0001](0001-reporting-cross-service-data-access.md) — reporting reads the
  `answers.score` values this algorithm produces, directly from TMS Postgres.
