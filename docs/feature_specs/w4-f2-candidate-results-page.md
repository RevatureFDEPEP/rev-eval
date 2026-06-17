# W4-F2 — Candidate Results Page with Suspense, Error Boundaries, and Chart

*Build the /results/[sessionId] page as a server-component-first screen with a recharts visualization, Suspense skeleton, and per-section error boundaries.*

* **Curriculum Fit**: Day 17 (Server components for data-heavy pages, data visualization with recharts, detail-view UI patterns, loading states with Suspense boundaries, error boundary patterns, responsive layout with Tailwind, accessibility fundamentals).
* **Prerequisites**: Day 17 topics.
* **Cross-Week Dependencies**: Requires W4-F1 (Candidate Results Reporting Endpoints) — the `GET /reports/user/{id}` endpoint must exist and return the correct envelope before the page can fetch and render it. Requires W3-F3 (Test-Taking Frontend Skeleton) — the AuthContext provider and pep_session cookie forwarding pattern established there are reused to authenticate the server-side results fetch. Requires W2-F1 (Nginx Routing) — the frontend must resolve `/results/*` through the gateway cleanly; without Nginx wired, cross-origin cookie forwarding breaks.
* **Time Estimate**: Without AI tools: 7–12 hours | With AI tools (Gemini/Claude Code): 3–6 hours

## Implementation Details

1. Create `frontend/app/results/[sessionId]/page.tsx` as an async server component. Fetch `GET /reports/user/{userId}` server-side using the `pep_session` cookie forwarded from `next/headers` and pass the envelope as a prop to child components.
2. Wrap the data-fetching section in a React Suspense boundary with a `loading.tsx` skeleton (placeholder cards matching the final layout) so the page chrome renders on first byte and the skeleton replaces the spinner pattern.
3. Wrap each data region (summary header, attempts table, chart) in a separate `error.tsx` boundary so a 500 from the reporting service blanks only its panel and shows a retry button, not the whole page.
4. Create a `<ChartWrapper>` client component that wraps recharts' `ResponsiveContainer` with consistent height, a standard `Tooltip`, a `Legend`, and an `aria-label`. Render a `BarChart` inside it showing per-question time-on-task or score-per-attempt, using the session data from the server component as the initial prop.
5. Apply the detail-view three-region pattern: headline summary (score + elapsed), tabular breakdown (one row per question, columns for result and time), and the chart below. Use Tailwind for a responsive single-column layout on mobile and a two-column layout on desktop.
