# Expected Milestones & Core Functionalities (Up to Day 20)

By Day 20, trainees are expected to have delivered the full results and trainer dashboard slice on top of the scaffolded reporting-and-analytics-service from Day 10, and enforced role-based authorization at both the API and frontend layers. The platform is now a complete vertical slice from candidate login through session scoring through trainer-visible aggregate reporting.

1. Results Reporting Backend (Day 16):
   * The reporting-and-analytics-service exposes read-heavy GET endpoints: a candidate results summary (GET /reports/user/{id}) and an attempt history list (GET /reports/user/{id}/attempts) with filtering by date range and test, pagination with page/size metadata, and stable default sort by submitted_at descending.
   * SQLAlchemy joins, aggregates (avg, count, sum), and subqueries produce the per-entity summary rows the frontend needs without requiring client-side re-aggregation.
   * The cross-service data access decision is made and documented: whether reporting reads test-management's Postgres directly (shared DB) or via HTTP calls, with the trade-offs named and recorded in an ADR.

2. Candidate Results Frontend (Day 17):
   * A server-component-first results page at /results/[sessionId] that fetches the GET /reports/user/{id} envelope once on the server and renders without a client-side spinner.
   * Suspense boundaries isolating the slow aggregate fetch so the page chrome renders instantly and the data region shows a skeleton during the database round trip.
   * Per-section error boundaries that prevent a single failing API call from blanking the entire page, with a retry CTA in the fallback.
   * A recharts bar chart visualizing per-question time-on-task or per-attempt score trend, wrapped in a reusable ChartWrapper component that enforces consistent sizing, tooltips, and accessible labels across the application.

3. Role-Based Authorization Gates and Trainer Dashboard Backend (Day 18):
   * A require_trainer FastAPI dependency that decodes the JWT using python-jose, reads the role claim from the verified payload (never from the request body), and raises a 403 for any non-trainer caller.
   * Aggregate reporting endpoints (GET /reports/aggregate, GET /reports/test/{id}) that compute GROUP BY, HAVING, and window function queries — pass rates, score distributions, per-question difficulty ranks — across the entire session and answers tables.
   * Multi-entity reporting that fans out across candidates, tests, and time simultaneously and returns a shape the frontend can render without a second compute pass.
   * Defense-in-depth: the backend enforces the role gate independently, so a candidate with curl or devtools cannot reach trainer-level data even if the frontend UI is cooperating.

4. Trainer Dashboard Frontend with Filtering and RBAC (Day 19):
   * Server-side role enforcement in Next.js middleware or per-page server components that redirects non-trainers away from /admin/* before any HTML or data is delivered.
   * Client-side route guards that conditionally render the dashboard navigation link based on the user's role from AuthContext, implemented as a UX affordance explicitly distinguished from the server-side security gate.
   * URL-synced, debounced filter controls (test selector, date-range picker) that drive the GET /reports/aggregate query parameters and make filtered views shareable via URL.
   * Full empty/loading/error state coverage across every page in the application: distinct components for each state, helpful copy rather than raw error strings, and a Suspense boundary or explicit loading skeleton for every data-fetching surface.


---

## Prioritized Feature Implementations for Days 16-20

The following 5 features are built exclusively using concepts taught in Days 1-20. They are listed in order of priority, starting with tasks that can be completed using topics available on Day 16, and ending with features that require Day 20 competencies.

### 1. Candidate Results Reporting Endpoints with Filtering and Pagination
*Build the read-heavy GET endpoints in reporting-and-analytics-service that serve the candidate results page: a summary envelope, a paginated attempt history, and per-entity aggregates.*
* **Curriculum Fit**: Day 16 (REST API design for read-heavy endpoints, filtering/pagination/sorting patterns in FastAPI, SQLAlchemy joins/aggregates/subqueries, per-entity aggregation query patterns, cross-service data access patterns, unit testing patterns for read endpoints).
* **Prerequisites**: Day 16 topics.
* **Cross-Week Dependencies**: Requires W2-F7 (Alembic Migrations & Scaffolded Domain) — reporting-and-analytics-service must already be scaffolded with a working Alembic environment and a postgres connection before new reporting tables can be migrated in. Requires W3-F2 (Scoring Engine) — the sessions and answers tables in test-management-service must be populated with scored data for the aggregation queries to have anything to read.
* **Time Estimate**: Without AI tools: 6–10 hours | With AI tools (Gemini/Claude Code): 3–5 hours
* **Implementation Details**:
  1. Add a sessions mirror table (or choose the direct-read cross-service pattern) to reporting-and-analytics-service and generate an Alembic migration. Document the decision — API call vs. direct DB read vs. event projection — in an ADR file.
  2. Implement GET /reports/user/{user_id} returning a summary envelope: total attempts, average score, best score, total time spent, and the most recent attempt. Use a single SQLAlchemy query with func.avg, func.count, func.sum, and a subquery for the most recent row.
  3. Implement GET /reports/user/{user_id}/attempts with query-parameter dependencies injected via a Pydantic dataclass: page (int, default 1), size (int, default 20, max 100), test_id (optional str), from/to (optional date), status (optional enum), sort (str pattern field:direction). Return a paginated envelope with items and total.
  4. Set up CORS for the reporting service to allow the frontend origin (http://localhost:3000) using FastAPI's CORSMiddleware, matching the Day 16 CORS configuration topic.
  5. Write unit tests for the read endpoints using pytest with a test database fixture, asserting correct pagination meta, correct filter application, and correct aggregate values from a seeded dataset.

### 2. Candidate Results Page with Suspense, Error Boundaries, and Chart
*Build the /results/[sessionId] page as a server-component-first screen with a recharts visualization, Suspense skeleton, and per-section error boundaries.*
* **Curriculum Fit**: Day 17 (Server components for data-heavy pages, data visualization with recharts, detail-view UI patterns, loading states with Suspense boundaries, error boundary patterns, responsive layout with Tailwind, accessibility fundamentals).
* **Prerequisites**: Day 17 topics.
* **Cross-Week Dependencies**: Requires W4-F1 (Candidate Results Reporting Endpoints) — the GET /reports/user/{id} endpoint must exist and return the correct envelope before the page can fetch and render it. Requires W3-F3 (Test-Taking Frontend Skeleton) — the AuthContext provider and pep_session cookie forwarding pattern established there are reused to authenticate the server-side results fetch. Requires W2-F1 (Nginx Routing) — the frontend must resolve /results/* through the gateway cleanly; without Nginx wired, cross-origin cookie forwarding breaks.
* **Time Estimate**: Without AI tools: 7–12 hours | With AI tools (Gemini/Claude Code): 3–6 hours
* **Implementation Details**:
  1. Create frontend/app/results/[sessionId]/page.tsx as an async server component. Fetch GET /reports/user/{userId} server-side using the pep_session cookie forwarded from next/headers and pass the envelope as a prop to child components.
  2. Wrap the data-fetching section in a React Suspense boundary with a loading.tsx skeleton (placeholder cards matching the final layout) so the page chrome renders on first byte and the skeleton replaces the spinner pattern.
  3. Wrap each data region (summary header, attempts table, chart) in a separate error.tsx boundary so a 500 from the reporting service blanks only its panel and shows a retry button, not the whole page.
  4. Create a <ChartWrapper> client component that wraps recharts' ResponsiveContainer with consistent height, a standard Tooltip, a Legend, and an aria-label. Render a BarChart inside it showing per-question time-on-task or score-per-attempt, using the session data from the server component as the initial prop.
  5. Apply the detail-view three-region pattern: headline summary (score + elapsed), tabular breakdown (one row per question, columns for result and time), and the chart below. Use Tailwind for a responsive single-column layout on mobile and a two-column layout on desktop.

### 3. Role-Based Authorization at the API Layer with Aggregate Reporting Queries
*Add JWT claim verification and a require_trainer dependency to the reporting service, then implement the GROUP BY, HAVING, and window-function queries that power the trainer dashboard.*
* **Curriculum Fit**: Day 18 (JWT claim verification and role enforcement, role-based authorization at the API layer, aggregate query patterns with GROUP BY/HAVING/window functions, multi-entity reporting query patterns, defense-in-depth security patterns, unit testing for authorization-gated endpoints).
* **Prerequisites**: Day 18 topics.
* **Cross-Week Dependencies**: Requires W4-F1 (Candidate Results Reporting Endpoints) — the reporting service must have working endpoints to add the require_trainer gate to; the aggregate endpoints extend the same service scaffolding. Requires W3-F2 (Scoring Engine) — the answers table and scoring data must be populated by the W3-F2 answer submission endpoint for GROUP BY and window-function queries to return meaningful results.
* **Time Estimate**: Without AI tools: 8–13 hours | With AI tools (Gemini/Claude Code): 4–7 hours
* **Implementation Details**:
  1. Add a require_trainer FastAPI dependency to reporting-and-analytics-service. Decode the Authorization header JWT using python-jose with the shared JWT_SECRET, reject tokens with an invalid signature or expired exp with a 401, and reject tokens where the verified role claim is not trainer with a 403. Never read role from the request body.
  2. Implement GET /reports/aggregate gated by require_trainer. Query across sessions and answers using GROUP BY test_id with aggregate columns: total attempts, distinct candidate count, avg score, pass rate (percentage of scores above a configurable threshold), and median time-to-complete using a window function percentile_cont.
  3. Implement GET /reports/test/{test_id}/questions gated by require_trainer. Return per-question difficulty: correct-answer rate, rank from hardest to easiest computed with RANK() OVER (ORDER BY correct_rate ASC), and a histogram bucket for score distribution.
  4. Write unit tests for the gated endpoints using pytest with a mock dependency override for require_trainer: assert that calls without the dependency return 403, calls with a candidate role return 403, and calls with a verified trainer role return 200 with the expected aggregate shape.
  5. Document the defense-in-depth posture: the backend gate is independent of the frontend, so the test suite explicitly exercises the gate via curl-equivalent requests that bypass all frontend route guards.

### 4. Trainer Dashboard Frontend with Server-Side RBAC, URL-Synced Filters, and Full State Coverage
*Build the /admin/dashboard page with Next.js server-side role enforcement, debounced URL-synced filter controls, aggregate chart visualizations, and empty/loading/error state coverage across every page.*
* **Curriculum Fit**: Day 19 (Aggregate data visualization, filtering and search UX patterns, role-based access enforcement in Next.js server-side, client-side route guards as UX, state-coverage UI for empty/loading/error states).
* **Prerequisites**: Day 19 topics.
* **Cross-Week Dependencies**: Requires W4-F3 (Role-Based Authorization at the API Layer) — the backend RBAC gate must be in place before the frontend enforcement is meaningful; the dashboard fetches trainer-only aggregate endpoints which return 403 without it. Requires W4-F2 (Candidate Results Page) — the ChartWrapper component is built in W4-F2 and reused here for the trainer aggregate charts. Requires W3-F3 (Test-Taking Frontend Skeleton) — the AuthContext provider built there supplies the role claim that drives client-side route guard conditional rendering. Requires W2-F1 (Nginx Routing) — Next.js middleware runs at the edge and intercepts /admin/* requests; if Nginx is not routing correctly, the middleware may not be reached for all entry points.
* **Time Estimate**: Without AI tools: 10–16 hours | With AI tools (Gemini/Claude Code): 5–9 hours
* **Implementation Details**:
  1. Add Next.js middleware (middleware.ts at the project root) that decodes the pep_session cookie, reads the role claim, and issues a redirect to /results if the claim is not trainer, before any /admin route handler runs. As a second layer, add an explicit role check inside the /admin/dashboard page.tsx server component that throws a redirect if the middleware was bypassed.
  2. Add conditional rendering to the sidebar and navigation components using AuthContext: hide the Dashboard link for candidates using role-aware client components. Add an explicit code comment clarifying this is a UX affordance and not the security layer.
  3. Implement filter controls as Next.js server-component-friendly inputs: a test-selector dropdown and a date-range picker whose values write to the URL query string using useRouter and useSearchParams. Wrap the text input in a 300ms debounce so it does not fire on every keystroke. The server component reads from searchParams to pre-render the filtered state with no client-side loading flicker.
  4. Render multi-series aggregate charts using the shared ChartWrapper component: a bar chart of pass rates per test and a line chart of attempt volume over time, both sourced from GET /reports/aggregate with the active filter parameters appended.
  5. Audit every page in the application against the empty/loading/error checklist: add a distinct EmptyState component with actionable copy for any list that can return zero items, verify Suspense boundaries cover every async server component, and confirm every error boundary has a working retry handler rather than a static error message.

### 5. Technical Debt Audit and ADR Documentation
*Identify, document, and rank the technical shortcuts taken across the four weeks, write Architecture Decision Records for the two or three most consequential choices, and produce a prioritized repayment backlog.*
* **Curriculum Fit**: Day 20 (Technical debt identification in own work, architectural decision reflection, defending AI-generated code, storytelling around technical work).
* **Prerequisites**: Day 20 topics, plus the full four weeks of accumulated decisions.
* **Cross-Week Dependencies**: Requires W4-F1 (Reporting Endpoints) — the cross-service data access decision (shared DB vs. API call vs. event projection) made in W4-F1 is one of the two required ADRs. Requires W3-F2 (Scoring Engine) — the partial-credit algorithm choice (full-match, Jaccard, or set-overlap) made in W3-F2 is the second required ADR. A meaningful debt inventory cannot be written without a substantially complete codebase, so all prior features should be at least partially implemented.
* **Time Estimate**: Without AI tools: 4–6 hours | With AI tools (Gemini/Claude Code): 2–4 hours
* **Implementation Details**:
  1. Conduct a structured walkthrough of the codebase to identify shortcuts: inline TODOs, missing input validation, hardcoded magic values, endpoints that return all rows without pagination, tests that use mocks where integration tests would give more confidence, and schema columns added without a migration.
  2. Write a debt inventory in docs/technical-debt.md. For each debt item, record the name, the location in code, the condition under which the debt matters (e.g., works fine at 50 users, breaks at 5,000), and an urgency rating (low / medium / high based on whether the current scale is already close to the limit).
  3. Write Architecture Decision Records (ADRs) in docs/adr/ for at least two decisions made during the project: the cross-service data access pattern chosen for reporting (shared DB vs. API call vs. event projection) and the scoring algorithm chosen for multi-select questions (full-match, Jaccard, or set-overlap). Each ADR follows the standard structure: context, decision, consequences, alternatives considered.
  4. For any code section that was drafted with AI assistance (Claude Code, Copilot, etc.), add an inline comment noting the AI involvement and the human review that followed. Prepare a short verbal defence of that section covering what the AI produced, what was changed, and why the final shape was chosen.
  5. Produce a one-page technical narrative combining what/why/how storytelling for the two most interesting features built, tying each to a concrete technical decision and the ADR that documents it.
