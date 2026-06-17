# W2-F2 — Scaffolding and Adding Unit Tests to Frontend and Backend Services

*Establish a robust automated unit testing foundation across the Next.js frontend and Python backend.*

* **Curriculum Fit**: Day 5 (Test authoring, multi-stage builds for testing, integration testing in compose) & Day 7 (CI pipeline optimization, test coverage reporting, quality gates, ruff/eslint linting).
* **Prerequisites**: Day 6 topics (relies on Day 5 and Day 7 concepts).
* **Required for**: W3-F2 (Scoring Engine — pytest must already be configured in test-management-service), W3-F5 (Integration Tests — pytest-asyncio and Alembic fixture setup builds on this scaffolding)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–4 hours

## Implementation Details

1. In the Next.js frontend, scaffold testing configurations using Vitest or Jest. Add unit tests for core presentation components, login layouts, and Zod client utility schemas.
2. In backend services (e.g., user-service and test-management-service), verify pytest is scaffolded. Create test databases and write parameterized unit tests targeting data models, repository CRUD functions, and Pydantic request validation schemas.
3. Update Dockerfiles to utilize multi-stage builds so tests can be run inside the container during CI, with a dedicated test stage that installs dev dependencies and runs pytest before the production image layer is assembled.
