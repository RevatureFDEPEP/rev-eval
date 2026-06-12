# Plan — W4-F2: Candidate Results Page (Suspense + Error Boundaries + Chart)

**Feature:** [W4-F2](../features/w4-f2-candidate-results-page.md) · Spec: `days_16_20_features.md` §2 (Day 17)
**Depends on:** W4-F1 ✅ (`GET /reports/user/{id}` + `/attempts` live, merged to `richardh` via PR #103), W3-F3 ✅ (AuthContext + cookie-forwarding server fetch), W2-F1 ✅ (gateway routing)
**Unblocks:** W4-F4 (trainer dashboard reuses `<ChartWrapper>`)
**Branch:** `richardh-feat-W4F2` off `richardh`

## Locked decisions

1. **Per-section boundaries via Next.js parallel routes.** The route is built as
   three independent data regions — `children` slot (summary headline),
   `@attempts` slot (history table), `@chart` slot — each with its **own
   `page.tsx`, `loading.tsx`, and `error.tsx`**. This is the only way to get the
   spec's literal "separate `error.tsx` around each data region": a plain
   segment `error.tsx` is whole-segment, and hand-rolled client boundaries
   can't catch server-component fetch throws. Each slot's `loading.tsx` is an
   automatic per-region Suspense boundary, satisfying the skeleton requirement
   with the same mechanism.
   - *Retry CTA:* `error.tsx` fallback calls `startTransition(() =>
     { router.refresh(); reset(); })` — `reset()` alone re-renders without
     refetching server data (known App Router gotcha).
   - *Gotcha:* each slot gets a `default.tsx` so soft navigation never 404s the
     parallel segment.
2. **Table = per-attempt rows; chart = score-per-attempt.** The W4-F1 envelope
   exposes `UserSummary` + paginated `AttemptItem`s only — **no per-question
   data exists** in the reporting API. The spec's chart choice is
   "per-question time-on-task **or** score-per-attempt" → score-per-attempt.
   For the table, detail-doc Step 3 itself names the region "attempts table";
   Step 5's "per-question breakdown" would require a new reporting endpoint
   (W4-F1/W4-F3 scope, not frontend scope) — the table renders one row per
   attempt (test, status, started, duration, score). Noted in the requirements
   review as a documented deviation.
3. **`[sessionId]` is a highlight anchor, not a fetch key.** Both W4-F1
   endpoints are user-scoped; `userId` comes from the JWT via `getSession()`
   server-side. The `sessionId` path param highlights that attempt's row in
   the table (and is validated as UUID-shaped; garbage → table just shows no
   highlight). This matches the spec, which routes by session but fetches
   `GET /reports/user/{id}`.
4. **`<ChartWrapper>` is generic-by-children.** Client component with props
   `{ title, ariaLabel, height?, children }` that owns `ResponsiveContainer`,
   consistent height, and the a11y wrapper (`role="img"` + `aria-label`);
   standard `Tooltip`/`Legend` styling exported as shared constants. The
   page-specific `BarChart` lives in a separate `ScoreTrendChart` client
   component composed inside it. W4-F4's aggregate charts reuse `ChartWrapper`
   + the shared tooltip/legend config with different recharts children.
5. **Cookie is `auth_token`** (repo reality), not the spec's `pep_session` —
   reuse `getSession()` / `lib/api/server.ts` `authedFetch` untouched.

## Context

- **Backend ready:** `GET /v1/api/reports/user/{user_id}` returns
  `{ user_id, total_attempts, avg_score, best_score, total_time_seconds,
  most_recent }`; `/user/{user_id}/attempts` returns `{ items, total, page,
  size }` with `AttemptItem { session_id, test_id, test_name, status,
  started_at, submitted_at, duration_seconds, score }`. Scores are 0–100
  percentages; non-SUBMITTED attempts have `score = null`
  (`services/reporting-and-analytics-service/src/schemas/report_schema.py`).
  Gateway already routes `^/v1/api/reports(/.*)?$`
  (`services/api-gateway-service/main.py:60`) — **no gateway change needed**.
- **Frontend plumbing exists:** `src/lib/session.ts` (`getSession()` →
  `userId` from JWT `sub`), `src/lib/api/server.ts` (`authedFetch` with Bearer
  forwarding, `cache: 'no-store'`), `src/middleware.ts` auth-gates every
  non-public path — `/results/*` gets the login redirect for free; no role
  restriction needed (own-results page for any authenticated role).
- **recharts `2.15.4` already in `frontend/package.json`**; shadcn `card.tsx`,
  `table.tsx`, `badge.tsx`, `separator.tsx` available in `components/ui/`.
  No `skeleton.tsx` — skeletons are `animate-pulse` Tailwind blocks shaped
  like the final cards (spec asks for layout-matching placeholders anyway).
- Reference pattern for async server page + boundaries:
  `src/app/take/[testId]/page.tsx` (W3-F3/W3-F7).
- No frontend test runner is configured (CI uses `--if-present`); the pass bar
  is `pnpm lint` + `pnpm build` + compose smoke (per repo testing reality).

## Step 0 — Branch & commit workflow

- `git fetch origin`; create **`richardh-feat-W4F2`** off **`origin/richardh`**.
  Work happens in the `w3-remediation` worktree where `richardh` is checked out
  elsewhere — use `git switch -c richardh-feat-W4F2 origin/richardh`.
- **First commit on the branch = this plan file.**
- One commit per milestone, Conventional Commits (`feat(w4-f2): …`).

## Milestones

### M1 — Report types + server fetchers

Files: `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/server.ts`.

- Add `UserReportSummary`, `ReportAttemptItem`, `ReportAttemptsPage` interfaces
  mirroring the W4-F1 schemas (nullable fields as `| null`).
- Add `getUserReportSummaryServer(userId)` → `GET /v1/api/reports/user/{id}`
  and `getUserReportAttemptsServer(userId, { page?, size? })` →
  `GET /v1/api/reports/user/{id}/attempts?...` to `server.ts`, following the
  existing `authedFetch` + `ServerApiError` pattern.

Commit: `feat(w4-f2): report envelope types + server-side fetchers`

### M2 — ChartWrapper + ScoreTrendChart

Files: `frontend/src/components/charts/ChartWrapper.tsx`,
`frontend/src/components/charts/ScoreTrendChart.tsx`.

- `ChartWrapper` (`'use client'`): fixed-height `ResponsiveContainer` shell,
  visible title, `role="img"` + `aria-label`, exports shared
  `chartTooltipProps` / `chartLegendProps` so every consumer (incl. W4-F4)
  renders identical tooltip/legend chrome.
- `ScoreTrendChart` (`'use client'`): recharts `BarChart` of score-per-attempt
  (x = attempt label/date, y = score 0–100, null-score attempts filtered),
  `Tooltip` + `Legend` from the shared props, composed inside `ChartWrapper`.

Commit: `feat(w4-f2): reusable ChartWrapper + score-per-attempt bar chart`

### M3 — `/results/[sessionId]` parallel-route page

Files (all under `frontend/src/app/results/[sessionId]/`):

```
layout.tsx              # chrome + three-region responsive grid (renders children/@attempts/@chart)
page.tsx                # summary headline region (async; fetches user summary)
loading.tsx             # summary skeleton
error.tsx               # summary fallback + retry
@attempts/page.tsx      # attempts table (async; fetches attempts page 1, highlights [sessionId] row)
@attempts/loading.tsx   # table skeleton
@attempts/error.tsx     # table fallback + retry
@attempts/default.tsx
@chart/page.tsx         # async; fetches attempts, renders <ScoreTrendChart>
@chart/loading.tsx      # chart-shaped skeleton
@chart/error.tsx        # chart fallback + retry
@chart/default.tsx
```

- `layout.tsx`: server component; `getSession()` gate (no session →
  `redirect('/')`, mirroring `/take`); Tailwind responsive grid — single
  column mobile, two-column desktop (summary spans full width, table left,
  chart right; chart below table on mobile) per spec region layout.
- Summary `page.tsx`: score (avg + best) and elapsed (total time) headline
  cards from `getUserReportSummaryServer`, plus most-recent-attempt line.
- `@attempts/page.tsx`: shadcn `Table`, one row per attempt — test name,
  status badge, started, duration, score; row matching `params.sessionId`
  visually highlighted.
- Each `error.tsx` (`'use client'`): panel-scoped fallback card with message +
  "Retry" button (`router.refresh()` + `reset()` in a transition) — a 500 from
  the reporting service blanks only its panel.
- Shared retry fallback extracted to
  `frontend/src/components/results/SectionErrorFallback.tsx` to keep the three
  `error.tsx` files one-liners.

Commit: `feat(w4-f2): results page with per-section suspense + error boundaries`

### M4 — Validation & fixes

- `pnpm lint` and `pnpm build` from `frontend/` — must pass clean.
- Compose smoke: `docker compose up --build -d`, log in as a seeded
  participant, take/submit a quiz if no scored data, then visit
  `/results/<sessionId>`:
  - summary score present in server-rendered HTML (no client spinner),
  - skeletons visible on slow load (DevTools throttle),
  - `docker compose stop reporting-and-analytics-service` → panels show retry
    fallbacks, page chrome + nav intact,
  - restart service → "Retry" buttons recover each panel.
- Fix anything found; commit only if code changed
  (`fix(w4-f2): …`).

### M5 — Requirements review & docs

- Re-read detail-doc Steps 1–5 + spec Implementation Details 1–5; verify each
  against the diff with file:line evidence. Record the Step-5 per-question →
  per-attempt deviation (decision 2) explicitly.
- Update `docs/features/w4-f2-candidate-results-page.md` (✅ steps + evidence +
  status) and the `docs/FEATURE_STATUS.md` W4-F2 row.

Commit: `docs(w4-f2): requirements review — mark feature complete`

## Testing & validation

| Check | Command / method | Pass bar |
|---|---|---|
| Lint | `cd frontend && pnpm lint` | zero errors |
| Build | `cd frontend && pnpm build` | compiles, `/results/[sessionId]` in route manifest |
| Server-first render | view-source on `/results/<id>` | summary data in initial HTML |
| Suspense skeletons | DevTools network throttle | chrome on first byte, skeleton per region |
| Error isolation | stop reporting service | only data panels fall back, retry works after restart |

No frontend unit runner exists in the repo (CI `--if-present`) — adding one is
out of W4-F2 scope; validation is lint + build + the compose smoke above.

## Push gate

Push `richardh-feat-W4F2` to origin **only if** lint + build pass **and** the
M5 review confirms every Step (with the documented decision-2 deviation noted
in the detail doc). Otherwise stop, leave the branch local, and report what's
outstanding.
