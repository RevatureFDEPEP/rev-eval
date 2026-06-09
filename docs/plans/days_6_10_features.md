# Expected Milestones & Core Functionalities (Up to Day 10)

By Day 10, trainees are expected to have established a stable, integrated, and well-routed local microservices ecosystem:

1. Integrated Compose Topology (Days 1–2 & Day 10):
   * A functional local cluster consisting of 5 FastAPI services (api-gateway, user-service, test-management-service, question-management-service, and reporting-and-analytics-service), 2 relational Postgres instances, 1 MongoDB instance, 1 MinIO instance, and the Next.js frontend.
   * Proper service dependency constraints (condition: service_healthy) ensuring database instances and dependency services start in order.

2. Nginx Edge Proxy & Path-Based Routing (Day 6):
   * Resolving the "502 by design" on Nginx (port 80). Trainees configure Nginx as the single entry point for clients, routing frontend static routes to the Next.js server and /api/v1/* routes down to the API Gateway.

3. Production-Ready CI/CD Pipeline (Days 3 & 7):
   * A parallelized matrix-based GitHub Actions pipeline.
   * Path filtering to prevent redundant builds (e.g., only running the user-service pipeline when services/user-service/** changes).
   * Quality Gates: Ruff for Python linting, ESLint for Next.js, Trivy for container vulnerability scans, and code coverage checks.

4. Document Modeling & Object Storage (Days 8–9):
   * MongoDB question collections managed via Beanie ODM.
   * File upload capability leveraging MinIO object storage.

5. Scaffolded Reporting microservice (Day 10):
   * Standing up the empty reporting-and-analytics-service based on standard repository conventions.
   * Wiring a dedicated reporting-postgres datastore to Alembic to track relational schema history and evolution.

---

## Prioritized Feature Implementations for Days 6–10

The following 7 features are built exclusively using concepts taught in Days 1–10. They are listed in order of priority, starting with tasks that can be completed using topics covered up to Day 6, and ending with ideas that require Day 10 concepts.

### 1. Nginx Path-Based Routing & Local TLS Setup (Reverse Proxy Hookup)
*Trainees wire Nginx to serve as the unified, secure entrance to the platform.*
* **Curriculum Fit**: Day 6 (Nginx Reverse Proxy, Local TLS/SSL, Path-based Routing).
* **Prerequisites**: Day 6 topics.
* **Status**: REQUIRED — Foundational entry point dependency for multiple features across Weeks 3 and 4. Completing this early unlocks the widest range of subsequent work.
* **Required for**: W3-F3 (Test-Taking Frontend Skeleton), W3-F6 (Playwright E2E and Smoke Script), W4-F2 (Candidate Results Page), W4-F4 (Trainer Dashboard)
* **Time Estimate**: Without AI tools: 3–5 hours | With AI tools (Gemini/Claude Code): 1–2 hours
* **Implementation Details**:
  1. Modify nginx/nginx.conf to act as a reverse proxy on port 80 (and port 443 for TLS).
  2. Configure routes: pass / and /_next/* to the frontend container (port 3000) and /api/v1/* to the api-gateway (port 8000).
  3. Generate local certificates (using mkcert or openssl) and mount them into Nginx.
  4. Update frontend environment variables to access the gateway securely via /api/v1 instead of cross-port requests, resolving local CORS issues.

### 2. Scaffolding and Adding Unit Tests to Frontend and Backend Services
*Establish a robust automated unit testing foundation across the Next.js frontend and Python backend.*
* **Curriculum Fit**: Day 5 (Test authoring, multi-stage builds for testing, integration testing in compose) & Day 7 (CI pipeline optimization, test coverage reporting, quality gates, ruff/eslint linting).
* **Prerequisites**: Day 6 topics (relies on Day 5 and Day 7 concepts).
* **Required for**: W3-F2 (Scoring Engine — pytest must already be configured in test-management-service), W3-F5 (Integration Tests — pytest-asyncio and Alembic fixture setup builds on this scaffolding)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–4 hours
* **Implementation Details**:
  1. In the Next.js frontend, scaffold testing configurations using Vitest or Jest. Add unit tests for core presentation components, login layouts, and Zod client utility schemas.
  2. In backend services (e.g., user-service and test-management-service), verify pytest is scaffolded. Create test databases and write parameterized unit tests targeting data models, repository CRUD functions, and Pydantic request validation schemas.
  3. Update Dockerfiles to utilize multi-stage builds so tests can be run inside the container during CI, with a dedicated test stage that installs dev dependencies and runs pytest before the production image layer is assembled.

### 3. Centralized Log Aggregation and Log Shipping
*Integrate Loki and Grafana to collect and monitor container logs from the reverse proxy and running microservices.*
* **Curriculum Fit**: Day 6 (Centralized logging with Loki/ELK, Docker networks).
* **Prerequisites**: Day 6 topics.
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours
* **Implementation Details**:
  1. Add Grafana and Loki services to docker-compose.yml.
  2. Configure the Loki logging driver or mount container standard logs into a Promtail agent container to ship all microservice standard logs to Loki.
  3. Establish a standard log formatting utility in Python microservices to print readable JSON logs.
  4. Set up a basic Grafana dashboard visualizing Nginx request codes, response times, and Python error trace counts.

### 4. Ruff Linting, ESLint, and Trivy Container Scanning in CI
*Extend the existing CI pipeline with static analysis and security scanning quality gates, completing the Day 7 candidate tasks called out in the pipeline comment.*
* **Curriculum Fit**: Day 7 (Code quality linting with Ruff and ESLint, container scanning with Trivy, test coverage reporting and quality gates, CI pipeline optimization).
* **Prerequisites**: Day 7 topics.
* **Status**: REQUIRED — Establishes the CI quality gates and service-container job patterns that Week 3 integration testing directly extends. Completing this before W3 prevents having to restructure the pipeline mid-week.
* **Required for**: W3-F5 (Integration Tests Against Real Postgres and Mongo Containers — CI Postgres/Mongo service-container steps extend this pipeline structure)
* **Time Estimate**: Without AI tools: 3–5 hours | With AI tools (Gemini/Claude Code): 1–2 hours
* **Note**: The ci-pipeline.yml already contains the comment `# NOTE: Trivy + Ruff scans added in W2 D7 by candidates (not seeded here)` — this feature is the intended completion of that placeholder.
* **Implementation Details**:
  1. Add a pyproject.toml at the repo root (or per-service) configuring Ruff with target-version = "py311", a line length of 88, and a rule set covering pyflakes (F), pycodestyle (E/W), isort (I), and the bugbear (B) rules. Add ruff check . as a CI step in the backend matrix job, after dependency installation and before pytest.
  2. Verify that the frontend lint step (pnpm lint) runs ESLint with a config that enforces the Next.js recommended rule set. Restore the step in ci-pipeline.yml to a hard failure (remove the || fallback added recently) so linting failures block the build rather than being silently skipped.
  3. Add a Trivy scan step to the backend matrix job using the aquasecurity/trivy-action GitHub Action. Configure it to scan the built Docker image, set exit-code: 1 so CRITICAL and HIGH CVEs fail the pipeline, and upload the SARIF report as a CI artifact for review.
  4. Add a coverage threshold to the pytest step: use --cov-fail-under=70 (or the threshold agreed with the cohort) so a drop in test coverage fails the build. Upload the coverage XML as a CI artifact so trends are visible across runs.

### 5. Direct-to-MinIO Diagram Uploads via Pre-Signed URLs
*Allow question creators to upload and attach architectural diagrams or screenshots directly to MinIO when authoring questions.*
* **Curriculum Fit**: Day 8 (MinIO Pre-signed URLs, MongoDB document modeling) & Day 9 (Direct-to-MinIO uploads).
* **Prerequisites**: Day 8 and 9 topics.
* **Required for**: W3-F1 (Quiz Session Creation Backend — question-management-service must have seeded question documents for the $sample aggregation to return results when a session is created)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–3 hours
* **Implementation Details**:
  1. Add an endpoint GET /questions/presigned-upload-url in question-management-service that uses boto3 to generate a pre-signed PUT URL for MinIO.
  2. In the Next.js frontend, implement a file-input field inside the question creator form.
  3. Use Zod client-side validation to restrict file types (e.g., .png, .jpg only) and cap file size at 5MB.
  4. Upon selecting a file, the frontend fetches the pre-signed URL, performs a direct PUT upload from the browser to MinIO, and saves the object key/path inside the question's MongoDB document.

### 6. Structured Question Authoring Interface
*Create a robust interactive form in the Next.js frontend to allow trainers to add new questions into the MongoDB database.*
* **Curriculum Fit**: Day 9 (Next.js 16 App Router, Form State Management with React Hook Form, Client-Side Validation with Zod, Component composition with Tailwind and Shadcn).
* **Prerequisites**: Day 9 topics.
* **Required for**: W3-F3 (Test-Taking Frontend Skeleton — question documents must exist in MongoDB for a session to sample and render a first question on page load)
* **Time Estimate**: Without AI tools: 5–8 hours | With AI tools (Gemini/Claude Code): 3–5 hours
* **Implementation Details**:
  1. Build an /admin/questions/create page in Next.js.
  2. Create a form structure using react-hook-form that dynamically alters its fields based on the selected question type (e.g., rendering options arrays for MCQ/MULTI vs. a simple checkbox for TRUE_FALSE).
  3. Formulate a Zod validation schema ensuring that MCQ questions have exactly one correct answer selected, MULTI questions have at least one correct answer selected, and all options have non-empty text.
  4. Submit the validated form payload via an API call through the API gateway.

### 7. Relational Schema Evolution using Alembic Migrations & Scaffolded Domain
*Extend the relational testing models to include a new "Question Categories" domain, scaffolding the database layers and updating schemas safely.*
* **Curriculum Fit**: Day 10 (Alembic Relational Evolution, FastAPI Service Conventions, and Compose composition).
* **Prerequisites**: Day 10 topics.
* **Required for**: W3-F1 (Quiz Session Creation Backend — the sessions table is a new Alembic migration on top of the existing test-management-service schema established here), W4-F1 (Candidate Results Reporting Endpoints — reporting-and-analytics-service Alembic environment must be initialized before new reporting migrations can run)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–3 hours
* **Implementation Details**:
  1. In test-management-service, add a new SQLAlchemy model Category (representing topics like "Python", "Docker", "Algorithms") and create a many-to-many relationship with Skill.
  2. Initialize Alembic inside services/test-management-service/ (if not done) or add models to the existing Alembic env context.
  3. Run alembic revision --autogenerate -m "Add categories and skills relationship" to generate the migration script, review the script, and run alembic upgrade head.
  4. Scaffold the standard repository, service, and router layers to allow trainers to fetch, create, and link Categories conforming to standard project conventions.
