# ADR W3-F3 — Test-Taking Frontend Skeleton

## Context

W3-F3 adds the `/take/[testId]` page that lets a participant sit a quiz. The
backend session API (W3-F1) is the only way to obtain questions; it hands out
one question at a time via `POST /v1/api/sessions/{id}/answer`. The frontend
must create a session, render questions polymorphically, and preserve answer
state across forward/backward navigation without full-page reloads.

Two architectural questions arise:

1. Where should the `/take/[testId]` route live in the Next.js App Router tree?
2. How should the client obtain question N+1 given that the backend is a
   sequential, one-at-a-time API?

## Decision

### Route placement — standalone (outside `(dashboard)`)

Place the page at `frontend/src/app/take/[testId]/page.tsx`, outside the
`(dashboard)` route group. This matches the spec exactly, keeps the exam UI
free of nav chrome, and mirrors the pattern in `feature_specs/w3-f3-*.md`.

### Question fetch — lazy on-demand via answer submission

`first_question` arrives in the `SessionRead` response from the server-side
session creation call. Subsequent questions are obtained by submitting the
current answer to `POST /v1/api/sessions/{id}/answer` (returns `next_question`).
`TestRunner` caches every fetched question in a `useState` array so backward
navigation ("Previous") never triggers an API call.

### AuthContext — server-reads JWT, client only sees plain object

The server component decodes the `auth_token` httpOnly cookie via the existing
`getSession()` utility (server-only module). It passes `{ id, email, role }` as
a plain prop to `AuthProvider`. Client code reads identity via `useAuth()` and
never touches the cookie or token string.

## Alternatives Considered

| Alternative | Reason rejected |
|---|---|
| Place route under `(dashboard)` | Adds nav chrome; contradicts spec path |
| Pre-fetch all questions server-side | Requires a bulk-fetch endpoint that does not exist |
| Read JWT on the client | Exposes token to `window`; violates security intent |

## Consequences

- Participants navigate to `/take/<id>` — a standalone full-screen page with no
  sidebar.
- First question renders in initial HTML (no client spinner); subsequent
  questions are fetched inline as the participant progresses.
- `AuthContext` is available throughout the `TestRunner` subtree; W3-F4, W4-F2,
  and W4-F4 can extend it without changing the provider shape.
- Going "Previous" is instant (cache hit); going "Next" on an unseen question
  requires one network round-trip.
