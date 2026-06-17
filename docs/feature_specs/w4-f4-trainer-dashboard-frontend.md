# W4-F4 — Trainer Dashboard Frontend with Server-Side RBAC, URL-Synced Filters, and Full State Coverage

*Build the /admin/dashboard page with Next.js server-side role enforcement, debounced URL-synced filter controls, aggregate chart visualizations, and empty/loading/error state coverage across every page.*

* **Curriculum Fit**: Day 19 (Aggregate data visualization, filtering and search UX patterns, role-based access enforcement in Next.js server-side, client-side route guards as UX, state-coverage UI for empty/loading/error states).
* **Prerequisites**: Day 19 topics.
* **Cross-Week Dependencies**: Requires W4-F3 (Role-Based Authorization at the API Layer) — the backend RBAC gate must be in place before the frontend enforcement is meaningful; the dashboard fetches trainer-only aggregate endpoints which return 403 without it. Requires W4-F2 (Candidate Results Page) — the ChartWrapper component is built in W4-F2 and reused here for the trainer aggregate charts. Requires W3-F3 (Test-Taking Frontend Skeleton) — the AuthContext provider built there supplies the role claim that drives client-side route guard conditional rendering. Requires W2-F1 (Nginx Routing) — Next.js middleware runs at the edge and intercepts `/admin/*` requests; if Nginx is not routing correctly, the middleware may not be reached for all entry points.
* **Time Estimate**: Without AI tools: 10–16 hours | With AI tools (Gemini/Claude Code): 5–9 hours

## Implementation Details

1. Add Next.js middleware (`middleware.ts` at the project root) that decodes the `pep_session` cookie, reads the role claim, and issues a redirect to `/results` if the claim is not `trainer`, before any `/admin` route handler runs. As a second layer, add an explicit role check inside the `/admin/dashboard/page.tsx` server component that throws a redirect if the middleware was bypassed.
2. Add conditional rendering to the sidebar and navigation components using AuthContext: hide the Dashboard link for candidates using role-aware client components. Add an explicit code comment clarifying this is a UX affordance and not the security layer.
3. Implement filter controls as Next.js server-component-friendly inputs: a test-selector dropdown and a date-range picker whose values write to the URL query string using `useRouter` and `useSearchParams`. Wrap the text input in a 300ms debounce so it does not fire on every keystroke. The server component reads from `searchParams` to pre-render the filtered state with no client-side loading flicker.
4. Render multi-series aggregate charts using the shared `ChartWrapper` component: a bar chart of pass rates per test and a line chart of attempt volume over time, both sourced from `GET /reports/aggregate` with the active filter parameters appended.
5. Audit every page in the application against the empty/loading/error checklist: add a distinct `EmptyState` component with actionable copy for any list that can return zero items, verify Suspense boundaries cover every async server component, and confirm every error boundary has a working retry handler rather than a static error message.
