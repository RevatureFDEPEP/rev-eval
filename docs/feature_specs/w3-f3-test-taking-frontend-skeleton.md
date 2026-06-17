# W3-F3 — Test-Taking Frontend Skeleton with Dynamic Routing and Auth Context

*Build the /take/[testId] Next.js page that mints a session server-side, renders questions polymorphically by type, and preserves answer state across forward and backward navigation.*

* **Curriculum Fit**: Day 13 (Dynamic routing with App Router parameters, server components for initial data fetching, polymorphic component rendering, multi-step navigation without state loss, authentication context propagation).
* **Prerequisites**: Day 13 topics.
* **Cross-Week Dependencies**: Requires W3-F1 (Quiz Session Creation Backend) — the page calls `POST /sessions` server-side on load; the endpoint must exist and return the correct contract shape. Requires W2-F1 (Nginx Routing) — the frontend must reach the API gateway through a single routed entry point rather than cross-origin direct port calls. Requires W2-F6 (Question Authoring Interface) — question documents must exist in MongoDB for a session to sample and render.
* **Required for**: W3-F4 (Auto-Saving Exam Client — the TestRunner component and answer Map state must exist as the base layer), W4-F2 (Candidate Results Page — the AuthContext provider and pep_session cookie forwarding pattern established here are reused), W4-F4 (Trainer Dashboard — the AuthContext provider supplies the role claim that drives client-side route guard rendering)
* **Time Estimate**: Without AI tools: 8–14 hours | With AI tools (Gemini/Claude Code): 4–7 hours

## Implementation Details

1. Create `frontend/app/take/[testId]/page.tsx` as an async server component. On render, read the `pep_session` cookie from `next/headers` and `POST /sessions` to test-management-service server-side, so the first question is in the initial HTML with no client spinner.
2. Pass the resulting session object as a prop to a `<TestRunner>` client component that owns all interactive state: `currentIndex` (number) and `answers` (`Map<string, number[]>`).
3. Inside TestRunner, implement a single dispatch function `renderQuestion(question)` that switches on `question.type` and renders either a `<SingleSelectQuestion>` (radio group) or `<MultiSelectQuestion>` (checkbox group) leaf component.
4. Implement Previous / Next navigation by incrementing or decrementing `currentIndex` in React state only, with no App Router navigation calls, so selections in the `answers` Map are preserved across question switches.
5. Create an `AuthContext` provider that reads display identity (`user_id`, `email`, `role`) from a server-fetched token validation call and exposes it to the client tree without ever placing the raw session cookie into `window` or JavaScript bundles.
