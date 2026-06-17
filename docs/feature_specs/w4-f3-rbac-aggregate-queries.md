# W4-F3 — Role-Based Authorization at the API Layer with Aggregate Reporting Queries

*Add JWT claim verification and a require_trainer dependency to the reporting service, then implement the GROUP BY, HAVING, and window-function queries that power the trainer dashboard.*

* **Curriculum Fit**: Day 18 (JWT claim verification and role enforcement, role-based authorization at the API layer, aggregate query patterns with GROUP BY/HAVING/window functions, multi-entity reporting query patterns, defense-in-depth security patterns, unit testing for authorization-gated endpoints).
* **Prerequisites**: Day 18 topics.
* **Cross-Week Dependencies**: Requires W4-F1 (Candidate Results Reporting Endpoints) — the reporting service must have working endpoints to add the `require_trainer` gate to; the aggregate endpoints extend the same service scaffolding. Requires W3-F2 (Scoring Engine) — the answers table and scoring data must be populated by the W3-F2 answer submission endpoint for GROUP BY and window-function queries to return meaningful results.
* **Time Estimate**: Without AI tools: 8–13 hours | With AI tools (Gemini/Claude Code): 4–7 hours

## Implementation Details

1. Add a `require_trainer` FastAPI dependency to reporting-and-analytics-service. Decode the `Authorization` header JWT using python-jose with the shared `JWT_SECRET`, reject tokens with an invalid signature or expired `exp` with a 401, and reject tokens where the verified `role` claim is not `trainer` with a 403. Never read role from the request body.
2. Implement `GET /reports/aggregate` gated by `require_trainer`. Query across sessions and answers using `GROUP BY test_id` with aggregate columns: total attempts, distinct candidate count, avg score, pass rate (percentage of scores above a configurable threshold), and median time-to-complete using a window function `percentile_cont`.
3. Implement `GET /reports/test/{test_id}/questions` gated by `require_trainer`. Return per-question difficulty: correct-answer rate, rank from hardest to easiest computed with `RANK() OVER (ORDER BY correct_rate ASC)`, and a histogram bucket for score distribution.
4. Write unit tests for the gated endpoints using pytest with a mock dependency override for `require_trainer`: assert that calls without the dependency return 403, calls with a candidate role return 403, and calls with a verified trainer role return 200 with the expected aggregate shape.
5. Document the defense-in-depth posture: the backend gate is independent of the frontend, so the test suite explicitly exercises the gate via curl-equivalent requests that bypass all frontend route guards.
