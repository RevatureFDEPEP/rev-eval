# W3-F1 — Quiz Session Creation Backend

*Implement the POST /sessions endpoint that mints an opaque session token, records server-authoritative timing, and fetches the first question from question-management-service.*

* **Curriculum Fit**: Day 11 (Cross-service HTTP integration via httpx, opaque token generation, server-authoritative state, random sampling from MongoDB, FastAPI routing and dependency injection).
* **Prerequisites**: Day 11 topics.
* **Cross-Week Dependencies**: Requires W2-F7 (Alembic migrations & scaffolded domain) — the sessions table is a new migration on top of the existing test-management-service schema. Requires the Docker Compose topology from W2 (question-management-service and its MongoDB must be healthy for the cross-service httpx call to succeed). Requires W2-F5 (MinIO & question bank) — question-management-service must have seeded question documents for `$sample` to return results.
* **Required for**: W3-F2 (Scoring Engine — the sessions table and session_id must exist before the answer endpoint can lock and advance them), W3-F3 (Test-Taking Frontend Skeleton — the page calls POST /sessions server-side on load; the endpoint must return the correct contract shape)
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours

## Implementation Details

1. Add a `sessions` table to test-management-service (`session_id` UUID, `test_id`, `user_id`, `session_token`, `server_now`, `expires_at`, `status`, `current_index`) and generate a migration with Alembic.
2. Implement `POST /sessions` in test-management-service. Generate the `session_id` with `secrets.token_hex` or `uuid4`, compute `expires_at` on the server from `test.duration_seconds`, and persist both before responding.
3. In the same handler, call question-management-service via an `httpx.AsyncClient` singleton with an explicit timeout to retrieve question IDs using MongoDB's `$sample` aggregation and to fetch the first question body.
4. Propagate the `X-Correlation-Id` header from the incoming request to all outbound httpx calls so distributed logs can be traced across services.
5. Return the `session_id`, `session_token`, `server_now`, `expires_at`, and the first question in the response body. The client never computes or stores timing state directly.
