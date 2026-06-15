# W4-F4 — Trainer Dashboard Frontend (Server-Side RBAC + URL-Synced Filters)

**Feature:** [docs/features/w4-f4-trainer-dashboard-frontend.md](../features/w4-f4-trainer-dashboard-frontend.md)
**Spec:** `days_16_20_features.md` §4 (Day 19)
**Depends on:** W4-F3 (✅ merged PR #109 — `require_trainer` + `/reports/aggregate`), W4-F2 (✅ — `<ChartWrapper>`), W3-F3 (✅ — AuthContext role), W2-F1 (✅ — nginx routing)
**Unblocks:** — (top of the Week 4 slice)
**Branch:** `richardh-feat-W4F4` off `richardh`

## Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Attempt-volume time-series | **New `GET /reports/timeseries`** (gated), `GROUP BY day(submitted_at), test_id`, returns `{date, test_id, test_name, attempts}`, honoring the shared `test_id`/`from`/`to` filters | `/aggregate` is collapsed per-test and can't supply a date axis; the sessions mirror already carries `submitted_at`, so this is the same tables + a different GROUP BY — no schema change. Granular rows let the frontend sum for a **total** line, draw **one line per quiz**, and the test-selector dropdown narrows to a **specific quiz** via `?test_id=`. Nothing consumes the reporting service yet except this feature, so it's additive/zero-risk. |
| Frontend `/admin/*` role gate | **TRAINER only** (ADMIN redirected, nav hidden) | Matches the W4-F3 backend gate (spec-strict TRAINER; ADMIN gets 403). Keeps frontend and backend consistent — an ADMIN never hits a 403 wall behind a page they could open. Diverges deliberately from `/trainer` (TRAINER+ADMIN); noted as a deviation. |
| Route location | `frontend/src/app/admin/dashboard/` (top-level segment) | Spec says `/admin/dashboard` verbatim; mirrors the existing top-level `results/` and `unauthorized/` segments. The `(dashboard)` group's `DashboardShell` keys `navBase` off `/trainer`\|`/participant`, so `/admin` lives outside it. |
| Step-5 state audit scope | New dashboard gets full empty/loading/error coverage + a reusable `EmptyState`; existing pages audited, only genuine gaps fixed (larger ones noted separately) | Avoids bundling unrelated W4-F2/W3 surfaces into W4-F4. |
| Filter debounce | A dependency-free `useDebouncedCallback` hook (300ms) on the keystroke-driven inputs (date range); dropdown writes immediately | No `use-debounce`/lodash in deps; spec wants the keystroke input debounced, not the select. |
| Day bucket | `func.date(submitted_at)` | Portable across Postgres + the aiosqlite unit fixture (same precedent as `_duration_seconds`' date handling). |

## Context

- **Reporting service (backend):** `/reports/aggregate` (per-test) and the
  `require_trainer` gate exist (`src/v1/dependencies/auth.py`). `AggregateQuery`
  + `ReportRepository._apply_filters` already implement `test_id`/`from`/`to`
  filtering over SUBMITTED sessions — the new timeseries query reuses both.
  Gateway `^/v1/api/reports(/.*)?$` already routes — **no ROUTES change**.
- **Frontend reuse surfaces (all present):**
  - `<ChartWrapper>` (`frontend/src/components/charts/ChartWrapper.tsx`) —
    `{title, ariaLabel, height=320, children}`, wraps `ResponsiveContainer` +
    exports `chartTooltipProps`/`chartLegendProps`. Reused for both charts.
  - W4-F2 results page (`src/app/results/[sessionId]/`) — the parallel-route +
    per-section `loading.tsx`/`error.tsx` + `SectionErrorFallback`
    (`src/components/results/SectionErrorFallback.tsx`) pattern to mirror.
  - Server fetchers in `src/lib/api/server.ts` via `authedFetch` (lifts the
    `auth_token` JWT from `getSession()`, forwards `Bearer`, base
    `API_GATEWAY_URL`). Add `getAggregateReportServer` + `getTimeseriesServer`.
  - Report types in `src/lib/api/types.ts` (W4-F2 envelopes). Add the W4-F3/F4
    aggregate + timeseries types.
  - `middleware.ts` already gates `/trainer`/`/participant`/`/dashboard` by
    decoding `auth_token` with `jose`'s `decodeJwt`. Extend the
    `roleProtectedRoutes` map for `/admin`.
  - Nav in `src/components/layout/dashboard-shell.tsx` (`navItems` memo). The
    `(dashboard)` shell is trainer/participant-scoped — the admin nav affordance
    is a small role-aware link, marked UX-only.
- **Tooling:** vitest (`pnpm test`), eslint (`pnpm lint`), `pnpm build`;
  recharts 2.15.4, date-fns 4.1.0 present; no debounce dep.

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` (already at `11ccce5`).
- Create **`richardh-feat-W4F4`** off `richardh` before any code change.
- **First commit on the branch = this plan file.**
- One commit per milestone (Conventional Commits).

## Milestones

### M1 — Backend: `GET /reports/timeseries` (gated)

Files: `services/reporting-and-analytics-service/src/schemas/report_schema.py`,
`src/repositories/report_repository.py`, `src/services/report_service.py`,
`src/v1/routes/report_route.py`, `tests/test_aggregate_endpoints.py` (extend),
`tests/conftest.py` (seed already has dated SUBMITTED sessions across tests).

- Schema: `TimeseriesPoint` (`date: date`, `test_id: int`, `test_name: str`,
  `attempts: int`); response `TimeseriesReport {items: [...]}`. Reuse
  `AggregateQuery` for the query params (`test_id`/`from`/`to` — drop
  `min_attempts`, or add a dedicated `TimeseriesQuery` mirroring those three).
- Repository `attempts_timeseries()` — SUBMITTED sessions, reuse
  `_apply_filters`, `GROUP BY func.date(TmsSession.submitted_at),
  TmsSession.test_id`, join `TmsTest.name`, `count(session_id)`,
  `ORDER BY date, test_id`.
- Service maps rows → `TimeseriesReport`. Route
  `GET /reports/timeseries`, `dependencies=[Depends(require_trainer)]`.
- Tests: trainer 200 with expected daily/per-test counts from the seed,
  `test_id` filter narrows series, `from`/`to` bound by `submitted_at`, gate
  (401/403) covered by the existing `require_trainer` matrix (one timeseries
  gate assertion added).
- Run `pytest --cov` (reporting). Commit:
  `feat(w4-f4): trainer attempt-volume timeseries endpoint (GROUP BY day, gated)`

### M2 — Frontend types + server fetchers

Files: `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/server.ts`.

- Types: `TestAggregateRow`, `AggregateReport {items, pass_threshold}`,
  `TimeseriesPoint`, `TimeseriesReport`, and a `ReportFilters`
  (`testId?`, `from?`, `to?`) helper type.
- `server.ts`: `getAggregateReportServer(filters)` →
  `/v1/api/reports/aggregate`, `getTimeseriesServer(filters)` →
  `/v1/api/reports/timeseries`, both via `authedFetch` with
  `URLSearchParams` (same shape as `getUserReportAttemptsServer`). A 403 throws
  `ServerApiError` (caught by the section error boundary).
- Commit: `feat(w4-f4): aggregate + timeseries types and server fetchers`

### M3 — Server-side RBAC (middleware + page guard)

Files: `frontend/src/middleware.ts`, `frontend/src/app/admin/dashboard/page.tsx`
(server component), `frontend/src/app/admin/dashboard/layout.tsx`.

- Extend `middleware.ts`: add `'/admin': ['TRAINER']` to `roleProtectedRoutes`;
  non-trainer hitting `/admin/*` → redirect (to `/unauthorized`, the existing
  segment, matching current mismatch behavior). Extract the pure
  `resolveAccess(pathname, role)` decision into a testable helper.
- `/admin/dashboard/page.tsx` (async server component): second-layer
  `getSession()` role check → `redirect('/unauthorized')` if not TRAINER (guards
  against middleware bypass), then renders the dashboard shell + filter bar +
  chart sections.
- Commit: `feat(w4-f4): server-side /admin RBAC (middleware + page guard)`

### M4 — Filters + aggregate charts (URL-synced, Suspense, error boundaries)

Files: `frontend/src/app/admin/dashboard/page.tsx` (read `searchParams`),
`frontend/src/components/admin/DashboardFilters.tsx` (client),
`frontend/src/components/admin/PassRateBarChart.tsx`,
`frontend/src/components/admin/AttemptVolumeChart.tsx`,
`frontend/src/lib/hooks/useDebouncedCallback.ts`,
`frontend/src/app/admin/dashboard/loading.tsx`,
`frontend/src/app/admin/dashboard/error.tsx`.

- `DashboardFilters` (client): test-selector `<Select>` (Radix, present) +
  date-range inputs; writes to the query string via `useRouter` +
  `useSearchParams`; date inputs debounced 300ms via the new hook; dropdown
  writes immediately. Filtered views shareable via URL.
- Page server component reads `searchParams` → builds `ReportFilters` → calls
  both fetchers server-side (no client loading flicker); passes data to charts.
  Each chart section wrapped in Suspense (`loading.tsx`) + error boundary
  (`error.tsx` → `SectionErrorFallback`).
- `PassRateBarChart` — `<ChartWrapper>` + recharts `BarChart`, pass rate per
  test from `/aggregate`. `AttemptVolumeChart` — `<ChartWrapper>` + `LineChart`;
  client-side derives **total** (sum across tests per date) when no test is
  selected, **one line per test** otherwise; `?test_id=` narrows to one series.
- Commit: `feat(w4-f4): URL-synced filters + pass-rate & attempt-volume charts`

### M5 — Client nav affordance (UX) + EmptyState + state audit

Files: `frontend/src/components/layout/dashboard-shell.tsx` (or the nav source),
`frontend/src/components/ui/empty-state.tsx` (new, reusable),
`frontend/src/app/admin/dashboard/*` (apply EmptyState to zero-row charts/lists),
plus targeted fixes to any genuine gaps found in the audit.

- Conditional "Dashboard (Admin)" nav link rendered only for TRAINER from
  AuthContext role, with an explicit comment: **UX affordance, not the security
  layer** (that's M3 + W4-F3).
- Reusable `<EmptyState>` (icon + actionable copy + optional CTA); use it for
  the no-attempts / no-tests chart states on the dashboard.
- Audit pass: confirm every async server component on the dashboard has a
  Suspense fallback and every error boundary a working retry; spot-check the
  W4-F2 results + W3 quiz surfaces and fix only genuine gaps, noting larger
  remediation as a separate item.
- Commit: `feat(w4-f4): admin nav affordance + reusable EmptyState + state audit`

### M6 — Frontend tests

Files: `frontend/src/components/admin/__tests__/*`,
`frontend/src/lib/**/__tests__/*` (match existing vitest test locations).

- `resolveAccess(pathname, role)` — TRAINER allowed on `/admin/*`, PARTICIPANT
  and ADMIN denied, non-admin paths unaffected.
- `DashboardFilters` — selecting a test / setting dates writes the expected
  query string; debounce coalesces rapid date edits (fake timers).
- Attempt-volume transform — total (sum across tests) vs per-quiz series vs
  single-quiz filter produce the expected line data.
- `<EmptyState>` renders copy/CTA; chart components render empty state on `[]`.
- Run `pnpm test`, `pnpm lint`, `pnpm build`. Commit:
  `test(w4-f4): RBAC resolver, URL-synced filters, chart transforms, EmptyState`

### M7 — Live compose smoke

No code; evidence for the review.

- `docker compose -p rev-eval up -d --build --wait` (rebuild frontend +
  reporting). Seed if needed.
- Trainer login → `/admin/dashboard`: 200, bar chart (pass rates) + line chart
  (attempt volume) render; select a test → URL gains `?test_id=`, both charts
  refilter server-side; date range narrows; shareable URL reloads filtered.
- Participant → `/admin/dashboard` redirected to `/unauthorized` (server-side,
  no dashboard HTML). Trainer nav shows the link; participant nav hides it.
- Through the gateway: `GET /v1/api/reports/timeseries` trainer 200 / participant
  403 (defense-in-depth still holds).

### M8 — Requirements review + docs

Files: `docs/features/w4-f4-trainer-dashboard-frontend.md`,
`docs/FEATURE_STATUS.md`.

- Re-read the 5 Steps + spec §4 Implementation Details; verify each against the
  diff with file:line + commit evidence; check off steps, record the M7 smoke
  transcript, note deviations (TRAINER-only `/admin` gate; `auth_token` not
  `pep_session`; redirect target `/unauthorized`; debounce on date inputs).
- Flip FEATURE_STATUS.md row W4-F4 → ✅ + update the summary.
- Commit: `docs(w4-f4): requirements review — mark feature complete`

## Testing & validation

| Check | Command (from) | Pass bar |
|---|---|---|
| Reporting unit tests | `pytest --cov` (`services/reporting-and-analytics-service/`) | All pass (40 existing + timeseries tests); ≥75% cov gate |
| Frontend unit tests | `pnpm test` (`frontend/`) | All pass (existing + new W4-F4 specs) |
| Frontend lint + build | `pnpm lint && pnpm build` (`frontend/`) | 0 errors, clean build |
| Live smoke | `docker compose -p rev-eval up -d --build --wait` + M7 matrix | trainer dashboard renders + filters refilter server-side; participant redirected to /unauthorized; timeseries 200/403 via gateway |

## Push gate

Push `richardh-feat-W4F4` to origin **only if** all tests pass **and** the M8
review confirms every Step. Otherwise stop, leave the branch local, report
what's outstanding.

## Out of scope (noted for later)

- Per-question difficulty drill-down UI for `/reports/test/{id}/questions`
  (W4-F3 endpoint exists; not in W4-F4's spec) — candidate follow-up.
- Full app-wide state-coverage remediation beyond genuine gaps — W4-F5 debt
  inventory if large.
- Retrofitting `<ChartWrapper>` onto the legacy `TrainerCharts.tsx`
  (`ChartContainer`-based) — separate cleanup.
