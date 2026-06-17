# W4-F1 — Candidate Results Reporting Endpoints with Filtering and Pagination

*Build the read-heavy GET endpoints in reporting-and-analytics-service that serve the candidate results page: a summary envelope, a paginated attempt history, and per-entity aggregates.*

* **Curriculum Fit**: Day 16 (REST API design for read-heavy endpoints, filtering/pagination/sorting patterns in FastAPI, SQLAlchemy joins/aggregates/subqueries, per-entity aggregation query patterns, cross-service data access patterns, unit testing patterns for read endpoints).
* **Prerequisites**: Day 16 topics.
* **Cross-Week Dependencies**: Requires W2-F7 (Alembic Migrations & Scaffolded Domain) — reporting-and-analytics-service must already be scaffolded with a working Alembic environment and a Postgres connection before new reporting tables can be migrated in. Requires W3-F2 (Scoring Engine) — the sessions and answers tables in test-management-service must be populated with scored data for the aggregation queries to have anything to read.
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours

## Implementation Details

1. Add a sessions mirror table (or choose the direct-read cross-service pattern) to reporting-and-analytics-service and generate an Alembic migration. Document the decision — API call vs. direct DB read vs. event projection — in an ADR file.
2. Implement `GET /reports/user/{user_id}` returning a summary envelope: total attempts, average score, best score, total time spent, and the most recent attempt. Use a single SQLAlchemy query with `func.avg`, `func.count`, `func.sum`, and a subquery for the most recent row.
3. Implement `GET /reports/user/{user_id}/attempts` with query-parameter dependencies injected via a Pydantic dataclass: `page` (int, default 1), `size` (int, default 20, max 100), `test_id` (optional str), `from/to` (optional date), `status` (optional enum), `sort` (str pattern `field:direction`). Return a paginated envelope with `items` and `total`.
4. Set up CORS for the reporting service to allow the frontend origin (`http://localhost:3000`) using FastAPI's `CORSMiddleware`, matching the Day 16 CORS configuration topic.
5. Write unit tests for the read endpoints using pytest with a test database fixture, asserting correct pagination meta, correct filter application, and correct aggregate values from a seeded dataset.
