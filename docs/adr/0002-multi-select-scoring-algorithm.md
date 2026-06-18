# ADR-0002: Partial-credit algorithm for multi-select scoring

- **Status:** Accepted
- **Date:** 2026-06-18
- **Feature:** W3-F2 (Scoring Engine)
- **Code:** `services/test-management-service/src/scoring/engine.py`

## Context

A quiz question of type `multi` has more than one correct option. When a
candidate selects a subset of the options, the scoring engine must turn that
selection into a score in `[0.0, 1.0]`. A binary all-or-nothing rule (the rule
we keep for single-select `mcq` / `true_false`) is defensible but harsh for
multi-select: a candidate who gets 4 of 5 options right scores the same `0.0` as
one who selected nothing. We wanted partial credit that is:

1. **Bounded** in `[0.0, 1.0]` and `1.0` only on an exact set match.
2. **Symmetric** in the two ways a candidate can be wrong — *missing* a correct
   option and *adding* a wrong one should both cost credit.
3. **Resistant to gaming** — "select every option" must not earn a high score.
4. **Deterministic and explainable** — a single ratio, no tuning constants, no
   I/O, so it is pure-unit-testable and ADR-defensible.

Three algorithms were on the table (the PEP brief names exactly these):
full-match, Jaccard index, and set-overlap.

## Decision

Use the **Jaccard index** for `multi`:

```
score = |A ∩ B| / |A ∪ B|     (A = correct set, B = submitted set)
is_correct = (score == 1.0)
```

Single-select types (`mcq`, `true_false`, and any unknown/`text` type) keep the
**exact-match** rule (`1.0` iff `A == B`, else `0.0`) — a single right answer
should be all-or-nothing. Both answer lists are normalized to a `frozenset` at
the boundary, so order and duplicates never affect the score, and `None`/`[]`
both collapse to the empty set.

## Consequences

- **Symmetric penalty (req. 2):** a missing correct option and an added wrong
  option each enlarge the union without enlarging the intersection, so both are
  penalized identically.
- **Anti-gaming (req. 3):** selecting every option drives the union to the full
  option set while the intersection stays at `|A|`, so the score collapses
  toward `|A| / |options|` instead of rewarding the candidate. This is covered
  by a dedicated regression test (`test_*_select_all_*` collapses below `1.0`).
- **Degenerate empty/empty case:** if both the key and the submission are empty,
  Jaccard is `0/0`; we define it as `1.0` (a vacuous full match). This is an
  authoring edge case, not a normal scored question, and is documented in the
  engine docstring.
- **`int`/`bool` set identity:** because Python hashes `True == 1`, a key of
  `[1]` and a submission of `[True]` compare equal. The engine deliberately does
  **not** coerce types — the answer key's own types decide equality. This is
  recorded as known behavior, with a test that pins it, rather than a defect.
- **Encoding coupling (see technical-debt.md):** the engine compares the two
  sets with no coercion, so both sides must use the same encoding. The contract
  is **1-indexed `option_id` integers** for mcq/multi (matching how qms stores
  `correct_answers`). A 0-indexed or option-text submission silently scores
  `0.0`; this contract is documented in `AnswerSubmit` and the engine, with
  regression tests, but it remains a cross-service coupling to watch.

## Alternatives considered

- **Full-match (all-or-nothing for multi too).** Simplest, but no partial
  credit — a near-perfect answer scores `0.0`. Rejected: fails the partial-credit
  goal that motivated the work.
- **Set-overlap:** `max(0, (correct_selected − incorrect_selected) / |A|)`.
  The PEP brief leans toward this one and it is a strong option, but it is
  **asymmetric**: it penalizes incorrect selections against `|A|` while not
  accounting for the union, so its behavior under over-selection is less clean to
  explain than Jaccard's single ratio. We chose Jaccard for symmetry and
  explainability and record set-overlap here as the runner-up — it is the natural
  thing to switch to if graders later want incorrect picks weighted differently.
