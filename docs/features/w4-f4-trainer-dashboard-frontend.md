# W4-F4 — Trainer Dashboard Frontend (Server-Side RBAC + URL-Synced Filters)

**Status:** ❌ Not Started
**Spec:** `days_16_20_features.md` §4 (Day 19)
**Depends on:** [W4-F3](w4-f3-rbac-aggregate-queries.md) (backend RBAC gate + aggregate endpoints must exist — the dashboard fetches trainer-only endpoints that 403 without it), [W4-F2](w4-f2-candidate-results-page.md) (reuses `<ChartWrapper>`), [W3-F3](w3-f3-test-taking-frontend-skeleton.md) (AuthContext supplies the role claim for client-side guards), [W2-F1](w2-f1-nginx-routing-tls.md) (Next.js middleware intercepts `/admin/*` at the edge; broken routing can bypass it)
**Unblocks:** — (top of the Week 4 slice; completes the trainer reporting surface)
**Last updated:** 2026-06-08

Build `/admin/dashboard` with Next.js server-side role enforcement, debounced
URL-synced filters, aggregate chart visualizations, and full
empty/loading/error state coverage across every page.

## Steps

- [ ] **1. Server-side role gate** — extend `frontend/src/middleware.ts` to
      decode the `auth_token` cookie, read the `role` claim, and redirect
      non-trainers away from `/admin/*` before any handler runs. Second layer:
      an explicit role check in `/admin/dashboard/page.tsx` that redirects if
      middleware was bypassed. *(Repo cookie is `auth_token`, not the spec's
      `pep_session`; middleware already exists for `/trainer` vs `/participant`
      — see [CLAUDE.md](../../CLAUDE.md).)*
- [ ] **2. Client-side guard (UX only)** — conditionally render the Dashboard
      nav link from AuthContext role. Code comment: this is a UX affordance, NOT
      the security layer (that's step 1 + W4-F3).
- [ ] **3. URL-synced debounced filters** — test-selector dropdown + date-range
      picker writing to the query string via `useRouter`/`useSearchParams`; text
      input debounced 300ms. Server component reads `searchParams` to pre-render
      the filtered state with no client loading flicker. Filtered views are
      shareable via URL.
- [ ] **4. Aggregate charts** — reuse `<ChartWrapper>` (W4-F2): bar chart of
      pass rates per test + line chart of attempt volume over time, both from
      `GET /reports/aggregate` with active filter params appended.
- [ ] **5. App-wide state coverage** — audit every page against
      empty/loading/error: a distinct `EmptyState` component with actionable
      copy for any zero-item list, Suspense boundaries on every async server
      component, and a working retry handler on every error boundary.

## Notes

- Role routing already exists in `middleware.ts` (`TRAINER`/`ADMIN` → `/trainer`)
  — extend it for `/admin/*` rather than adding a parallel mechanism.
- Step 5 is a cross-cutting audit, not scoped to the dashboard — it touches the
  results page (W4-F2) and the quiz UI (W3-F3/W3-F4) too.

## Remaining

All steps.
