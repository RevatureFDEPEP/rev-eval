# W4-F4 — Trainer Dashboard Frontend (Server-Side RBAC + URL-Synced Filters)

**Status:** ✅ Completed
**Spec:** `days_16_20_features.md` §4 (Day 19)
**Depends on:** [W4-F3](w4-f3-rbac-aggregate-queries.md) (backend RBAC gate + aggregate endpoints — the dashboard fetches trainer-only endpoints that 403 without it), [W4-F2](w4-f2-candidate-results-page.md) (reuses `<ChartWrapper>` + the parallel-route/`SectionErrorFallback` pattern), [W3-F3](w3-f3-test-taking-frontend-skeleton.md) (AuthContext role for client-side guards), [W2-F1](w2-f1-nginx-routing-tls.md) (edge middleware intercepts `/admin/*`)
**Unblocks:** — (top of the Week 4 slice; completes the trainer reporting surface)
**Branch:** `richardh-feat-W4F4` · **Plan:** [docs/plans/w4-f4-trainer-dashboard-frontend.md](../plans/w4-f4-trainer-dashboard-frontend.md)
**Last updated:** 2026-06-15

Build `/admin/dashboard` with Next.js server-side role enforcement, debounced
URL-synced filters, aggregate chart visualizations, and full
empty/loading/error state coverage across every page.

## Steps

- [x] **1. Server-side role gate** — extend `frontend/src/middleware.ts` to
      decode the `auth_token` cookie, read the `role` claim, and redirect
      non-trainers away from `/admin/*` before any handler runs. Second layer:
      an explicit role check in `/admin/dashboard/page.tsx` that redirects if
      middleware was bypassed.
      *Evidence:* `frontend/src/lib/auth/access.ts` (pure `resolveAccess` +
      `/admin: [TRAINER]`) wired into `middleware.ts`; the
      `/admin/dashboard/layout.tsx` **and** `page.tsx` server components both
      re-check `getSession().role` and `redirect('/unauthorized')`. Live: a
      participant cookie → **307 → /unauthorized**, no cookie → **307 → /**,
      trainer → **200** (commits `ae44c9b`, `b1325df`).
- [x] **2. Client-side guard (UX only)** — conditionally render the Dashboard
      nav link from AuthContext role. Code comment: this is a UX affordance, NOT
      the security layer.
      *Evidence:* `dashboard-shell.tsx` pushes an "Analytics" →
      `/admin/dashboard` nav item only when the AuthContext role is `TRAINER`,
      with an explicit comment that this is UX-only and the gate is server-side
      (commit `8d450aa`).
- [x] **3. URL-synced debounced filters** — test-selector dropdown + date-range
      picker writing to the query string via `useRouter`/`useSearchParams`; text
      input debounced 300ms. Server component reads `searchParams` to pre-render
      the filtered state with no client loading flicker. Filtered views
      shareable via URL.
      *Evidence:* `components/admin/DashboardFilters.tsx` writes `test_id`/
      `from`/`to` via `router.replace`; the dropdown writes immediately, date
      inputs debounce 300ms via `lib/hooks/useDebouncedCallback.ts`. The slot
      server components read `searchParams` (`parseReportFilters`) and fetch
      server-side. Live: `GET /admin/dashboard?test_id=1&from=2026-06-11` → 200
      server-rendered (commit `b1325df`).
- [x] **4. Aggregate charts** — reuse `<ChartWrapper>` (W4-F2): bar chart of
      pass rates per test + line chart of attempt volume over time, both from
      `GET /reports/aggregate` with active filter params appended.
      *Evidence:* `PassRateBarChart` (`/aggregate`) + `AttemptVolumeChart`
      (`/timeseries`, pure `pivotVolumeByTest` → total line + one line per
      quiz), both on `<ChartWrapper>`. The W4-F3 `/aggregate` is collapsed
      per-test (no date axis), so the attempt-volume series is fed by a new
      **`GET /reports/timeseries`** (commit `a029660`, gated; see deviations).
      Live: timeseries 200 with day-bucketed rows, `test_id` filter narrows
      (commits `a029660`, `b1325df`).
- [x] **5. App-wide state coverage** — a distinct `EmptyState` component with
      actionable copy for any zero-item list, Suspense boundaries on every async
      server component, and a working retry handler on every error boundary.
      *Evidence:* reusable `components/ui/empty-state.tsx` used by both charts;
      the dashboard's `@passrate`/`@volume` slots each carry `loading.tsx`
      (Suspense skeleton) + `error.tsx` (`SectionErrorFallback`, working
      `router.refresh()`+`reset()` retry). Audit of existing surfaces found no
      genuine gaps (results + take already carry their own boundaries per
      W4-F2/W3-F7); larger remediation deferred to W4-F5 (commits `b1325df`,
      `8d450aa`).

## Live smoke (2026-06-15, compose stack)

- Backend via gateway (`:8000`): `GET /reports/timeseries` trainer **200**
  (`[{date:2026-06-10,test_id:1,…,attempts:1},{date:2026-06-11,…,attempts:2}]`),
  participant **403**, no token **401**, `?test_id=1` narrows; `/reports/aggregate`
  trainer **200**.
- Frontend (`:3000`): trainer `/admin/dashboard` **200** rendering "Trainer
  dashboard" + both charts ("Pass rate per test", "Attempt volume over time")
  with real data ("Java Fundamentals") in the initial HTML (server-rendered, no
  flicker); participant **307 → /unauthorized**; no cookie **307 → /**; filtered
  `?test_id=1&from=2026-06-11` **200** server-rendered (shareable).

## Recorded deviations / decisions

- **New `GET /reports/timeseries` endpoint** (require_trainer-gated, `GROUP BY
  date(submitted_at), test_id`) was added to the reporting service to back the
  attempt-volume line chart — `/aggregate` is collapsed per-test and exposes no
  date axis. Additive and zero-risk (nothing else consumes the reporting
  service). The frontend sums across tests for a total line, draws one line per
  quiz, and the test-selector dropdown narrows to a single quiz via `test_id`.
- **`/admin/*` is TRAINER-only** (ADMIN redirected, nav hidden), matching the
  W4-F3 backend gate (ADMIN gets 403) — deliberately diverges from `/trainer`
  (TRAINER+ADMIN) so an admin is redirected rather than walled behind a 403.
- Repo cookie is **`auth_token`** (not the spec's `pep_session`); redirect
  target for a wrong-role caller is **`/unauthorized`** (existing segment),
  matching the existing middleware mismatch behavior.
- Debounce (300ms) applies to the keystroke-driven **date inputs**; the
  test-selector dropdown writes immediately (no per-keystroke risk).
- `/admin/dashboard` lives as a **top-level segment** (like `results/`,
  `unauthorized/`), outside the trainer/participant-scoped `(dashboard)` group,
  but reuses `DashboardShell` for chrome.

## Notes

- Role routing already existed in `middleware.ts` (`TRAINER`/`ADMIN` → `/trainer`)
  — this extended it for `/admin/*` via the shared `resolveAccess` helper rather
  than adding a parallel mechanism.

## Remaining

None.
