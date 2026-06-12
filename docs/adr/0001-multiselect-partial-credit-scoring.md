# ADR 0001: Multi-select partial-credit scoring

## Status

Accepted

## Context

The Week 3 scoring spec names Jaccard overlap for multi-select partial credit:

```text
|correct answers intersect submitted answers| / |correct answers union submitted answers|
```

The scoring engine currently uses a penalty-based overlap formula instead:

```text
earned = clamp((true_positives - false_positives) / |correct_answers|, 0, 1)
```

For example, with correct answers `{1, 2, 3}` and submitted answers `{1, 2, 4}`,
Jaccard awards `0.5`, while the penalty-based formula awards `0.33`.

## Decision

Keep the penalty-based formula for multi-select quiz questions and document it as
an intentional deviation from Jaccard.

## Rationale

The main product risk in multi-select questions is broad guessing. Jaccard gives
partial credit when a participant selects extra wrong answers, and a
select-everything strategy can still earn non-zero credit. The penalty-based
formula rewards correct selections while making wrong selections reduce the
score, so a select-everything strategy trends toward zero.

This behavior is stricter than Jaccard, but it better matches the assessment
goal: credit should reflect knowing the correct options, not just maximizing
overlap by selecting many options.

## Consequences

- Multi-select scoring is harsher than the named spec formula.
- The formula is deterministic and auditable through recorded true-positive,
  false-positive, and false-negative counts.
- Per-question `is_correct` remains true only for exact set matches.
- Future reporting should label this as penalty-based partial credit, not
  Jaccard scoring.

## Implementation

Implemented in:

- `services/test-management-service/src/scoring/partial_credit.py`
- `services/test-management-service/tests/test_scoring.py`

