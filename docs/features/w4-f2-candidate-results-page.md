# W4-F2 — Candidate Results Page (Suspense + Error Boundaries + Chart)

**Status:** ❌ Not Started
**Spec:** `days_16_20_features.md` §2 (Day 17)
**Depends on:** [W4-F1](w4-f1-results-reporting-endpoints.md) (`GET /reports/user/{id}` must exist + return the correct envelope), [W3-F3](w3-f3-test-taking-frontend-skeleton.md) (reuses the AuthContext provider + cookie-forwarding pattern for the server-side fetch), [W2-F1](w2-f1-nginx-routing-tls.md) (frontend resolves `/results/*` through the gateway; cross-origin cookie forwarding breaks without it)
**Unblocks:** [W4-F4](w4-f4-trainer-dashboard-frontend.md) (the `<ChartWrapper>` built here is reused for trainer aggregate charts)
**Last updated:** 2026-06-08

Build `/results/[sessionId]` as a server-component-first screen with a recharts
visualization, a Suspense skeleton, and per-section error boundaries.

## Steps

- [ ] **1. Server-component page** —
      `frontend/src/app/results/[sessionId]/page.tsx` (async server component).
      Fetch `GET /reports/user/{userId}` server-side using the `auth_token`
      cookie from `next/headers`; pass the envelope as a prop to children.
      *(Spec writes `pep_session`; repo cookie is `auth_token` — follow the
      repo, see [CLAUDE.md auth flow](../../CLAUDE.md).)*
- [ ] **2. Suspense skeleton** — wrap the data-fetching section in a Suspense
      boundary with a `loading.tsx` skeleton (placeholder cards matching final
      layout) so chrome renders on first byte.
- [ ] **3. Per-section error boundaries** — separate `error.tsx` around each
      data region (summary header, attempts table, chart) so a 500 blanks only
      its panel and shows a retry CTA, not the whole page.
- [ ] **4. ChartWrapper + BarChart** — `<ChartWrapper>` client component
      wrapping recharts `ResponsiveContainer` with consistent height, standard
      `Tooltip`, `Legend`, and `aria-label`. Render a `BarChart` of per-question
      time-on-task or score-per-attempt from the server-fetched data. **Reused
      by W4-F4** — design the API for trainer aggregate charts too.
- [ ] **5. Detail-view layout** — three regions: headline summary (score +
      elapsed), tabular per-question breakdown, chart below. Tailwind responsive:
      single-column mobile, two-column desktop.

## Notes

- Cookie name: repo uses **`auth_token`** (httpOnly), not the spec's
  `pep_session`; reuse existing `getSession()` / `lib/api/server.ts` plumbing.
- `<ChartWrapper>` is a shared component — its consistent-sizing/tooltip/a11y
  contract is the reuse surface for W4-F4; don't inline chart config per page.

## Remaining

All steps.
