# W3-F2 — Scoring Engine with Exact-Match and Partial-Credit Algorithms

*Build pure, deterministic scoring functions for single-select and multi-select questions, then wire them into the answer submission endpoint with pessimistic locking.*

* **Curriculum Fit**: Day 12 (Deterministic scoring, partial-credit algorithms, database transactions, pessimistic locking, idempotency for retried mutations, state finalization and immutability).
* **Prerequisites**: Day 12 topics.
* **Cross-Week Dependencies**: Requires W3-F1 (Quiz Session Creation Backend) — the sessions table, session_id, and current_index column must exist before the answer endpoint can lock and advance them. Requires W2-F2 (Unit Test Scaffolding) — pytest must already be configured in test-management-service for the parameterized scoring tests to run in CI.
* **Required for**: W3-F4 (Auto-Saving Exam Client — the PATCH /sessions/{id}/draft endpoint and session state machine established here are the base layer), W4-F1 (Candidate Results Reporting Endpoints — sessions and answers tables must be populated with scored data for aggregation queries), W4-F3 (Role-Based Authorization and Aggregate Queries — answers table data required for GROUP BY and window-function queries), W4-F5 (Technical Debt Audit — the scoring algorithm choice is one of the two required ADRs)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours

## Implementation Details

1. Create a scoring module in test-management-service (e.g., `src/scoring/exact_match.py` and `src/scoring/partial_credit.py`). Each file exposes a single pure function `score_question(question_type, correct_answers, submitted_answers) -> ScoreResult` with no database access or side effects.
2. Implement the `POST /sessions/{id}/answer` endpoint. Wrap the read-modify-write in an explicit transaction and acquire a `SELECT FOR UPDATE` lock on the session row before reading `current_index`, so concurrent retries queue rather than race.
3. Accept an `Idempotency-Key` header and store seen keys in a dedup table. On a duplicate key, return the prior response without re-scoring.
4. After scoring, advance `current_index`. If it reaches the final question, transition session status to `submitted`, record `submitted_at`, and reject all further answer mutations with a 409.
5. Write parameterized pytest cases covering exact-match, full-match, Jaccard, and partial-credit scenarios with a matrix of correct and incorrect answer combinations, using AI-assisted test authoring where appropriate.
