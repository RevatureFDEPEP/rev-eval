# ADR 0001 — Candidate Results Page Data Contract (W4-F2)

- **Status:** Accepted
- **Date:** 2026-06-17
- **Feature:** W4-F2 — Candidate Results Page (`services/features-list.md` §"Days 16–20", item 2)
- **Supersedes / relates to:** `services/reporting-and-analytics-service/adr/0001-cross-service-data-access.md` (W4-F1 — the upstream endpoints this page consumes)

## Context

W4-F2 builds `app/results/[sessionId]/page.tsx`: a server-component-first candidate
results screen with a headline summary, a tabular breakdown, and a recharts
visualization (spec items R1–R5).

The spec describes the page in terms that pre-date the *realized* W4-F1 contract,
and the two do not line up:

1. **The route segment is `[sessionId]`, but the only F1 endpoint is keyed by
   `user_id`** (`GET /reports/user/{user_id}` → `UserSummaryResponse`;
   `GET /reports/user/{user_id}/attempts` → `PaginatedAttempts`). F1 exposes **no**
   per-session lookup and **no** session→user resolution.
2. **The spec's table says "one row per question" and the chart mentions
   "per-question time-on-task"**, but F1 returns **per-attempt** rows only
   (`AttemptItem`: `score`, `correct_count`, `total_answered`, `time_spent_seconds`,
   `status`, timestamps). There is no per-question data anywhere in the F1 envelopes.

W4-F1 is frozen and PR-raised under the locked **split-PR discipline** (PR-A scaffold
→ PR-B F1 → F2–F5 each their own PR). Reopening F1 to add a per-question or
per-session endpoint would violate that discipline and re-scope a graded deliverable.

The platform's identity model is **header-trust**: the gateway verifies the JWT and
injects `X-User-Id`/`X-User-Role`; F1's `require_self_or_trainer` lets a participant
read only their own reports. The frontend server component already has the
authenticated identity via `getSession()` (the `auth_token` cookie → `userId`).

## Decision

**Consume F1 exactly as built; reconcile the spec's wording to F1's realized contract
rather than changing F1.**

1. **Identity (D1):** Keep the spec's `/results/[sessionId]` URL. Derive `userId`
   from the authenticated session (`getSession().userId`), **not** from the route.
   `sessionId` selects the *featured* attempt: the page fetches the caller's own
   per-user report and highlights the matching attempt. If `sessionId` is not among
   the caller's own attempts, return `notFound()`. The page only ever fetches the
   caller's own data, so there is no IDOR surface and no need for a session→user
   lookup F1 doesn't offer.
2. **Table (D2):** Render **one row per attempt** (test, status, score,
   correct/total, time spent), using `AttemptItem`. A literal per-question table is
   deferred to a future slice that adds a per-session/per-question F1 endpoint.
3. **Chart (D3):** Render a **score-per-attempt** BarChart. The spec explicitly
   offers "per-question time-on-task **or** score-per-attempt"; only the latter is
   backed by F1 data, so it is the spec-compliant choice.
4. **Scope (D7):** F2 is candidate-facing and **self-only**. F1's
   trainer-views-anyone authorization path is exercised by W4-F4 (trainer dashboard),
   not here.

## Consequences

- **Positive:** No backend change; the frozen F1 PR is untouched and the split-PR
  discipline holds. No IDOR — the page is structurally incapable of reading another
  user's data. The spec's route URL is preserved. `sessionId` carries real meaning
  (which attempt to feature) and supports a future post-submit redirect to
  `/results/{justFinishedSessionId}`.
- **Negative / debt:** The page cannot show a per-question breakdown until a future
  slice adds the endpoint; the "one row per question" wording in the spec is
  deliberately unmet and recorded here as known debt (candidate for the W4-F5 debt
  inventory). The page is coupled to F1's per-attempt envelope shape; an F1 envelope
  change is a "re-verify F2" signal.

## Alternatives considered

- **Rename the route to `/results/[userId]`** — exact param/endpoint match, but
  deviates from the spec's literal URL and loses the "featured attempt" affordance.
- **Add a per-question / per-session endpoint to F1** — would let the table be
  literally per-question, but reopens a frozen, PR-raised service and breaks the
  locked split-PR discipline. Rejected.
- **Drop the dynamic segment (`/results`)** — simplest "my results" UX, but discards
  the spec's dynamic route and the post-submit deep-link path. Rejected.

## Related implementation decision (not contested, recorded for traceability)

- **Per-region error isolation (D4):** Next.js `error.tsx` is route-scoped and cannot
  blank a single panel. To satisfy R3 ("a 500 blanks only its panel + retry button,
  not the whole page"), the page uses a route-level `error.tsx` **plus** a reusable
  client `RegionErrorBoundary` wrapping each of the three regions.
