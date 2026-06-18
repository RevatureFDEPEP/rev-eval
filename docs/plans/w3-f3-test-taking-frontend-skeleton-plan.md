# w3-f3 Implementation Plan — Test-Taking Frontend Skeleton

## Goal

Build the `/take/[testId]` Next.js page that creates a quiz session server-side
on load (calling the W3-F1 `POST /v1/api/sessions/` endpoint), renders questions
polymorphically by type, and preserves answer state across Prev/Next navigation
without App Router calls. Adds an `AuthContext` provider that exposes `user_id`,
`email`, and `role` to the client tree without ever touching the raw JWT on the
client side.

---

## Affected Files

| Action | Path |
|--------|------|
| CREATE | `frontend/src/app/take/[testId]/page.tsx` |
| CREATE | `frontend/src/app/take/[testId]/TestRunner.tsx` |
| CREATE | `frontend/src/context/AuthContext.tsx` |
| CREATE | `frontend/src/lib/api/sessions.ts` |
| CREATE | `frontend/src/__tests__/app/take/TestRunner.test.tsx` |
| CREATE | `frontend/src/__tests__/context/AuthContext.test.tsx` |
| CREATE | `docs/adr/w3-f3-test-taking-frontend-skeleton.md` |
| UPDATE | `docs/features/w3-f3-test-taking-frontend-skeleton.md` |
| UPDATE | `docs/FEATURE_STATUS.md` |
| UPDATE | `docs/index.md` |

---

## Key Background

- **Backend session API (W3-F1)**: `POST /v1/api/sessions/` → returns `SessionRead`
  with `session_id`, `expires_at`, `first_question` (first `QuizQuestionOut`).
  Subsequent questions are fetched by calling `POST /v1/api/sessions/{id}/answer`
  which returns `AnswerResponse` with `next_question`.
- **Existing quiz components** (reuse, do not recreate):
  - `frontend/src/components/quiz/QuestionCard.tsx` — dispatches by `question_type`
  - `frontend/src/components/quiz/MCQQuestion.tsx`, `MultiQuestion.tsx`, `TrueFalseQuestion.tsx`
- **`getSession()`** at `frontend/src/lib/session.ts`: server-only utility that
  decodes the `auth_token` httpOnly cookie into `{ userId, email, role, token }`.
- **BFF proxy**: `frontend/src/app/api/v1/[...path]/route.ts` forwards client-side
  `/api/v1/*` calls to the API gateway. Client-side answer submissions go here.
- **Server-side gateway calls**: page.tsx calls the gateway directly with bearer token
  (same pattern as `frontend/src/app/api/auth/me/route.ts`).

---

## Implementation Steps

### 1. `AuthContext.tsx`

Create `frontend/src/context/AuthContext.tsx` as a `'use client'` module:

```tsx
'use client';
import { createContext, useContext } from 'react';

export interface AuthUser {
  id: number;
  email: string;
  role: string;
}

const AuthContext = createContext<AuthUser | null>(null);

export function AuthProvider({ user, children }: { user: AuthUser; children: React.ReactNode }) {
  return <AuthContext.Provider value={user}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthUser {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
```

### 2. `lib/api/sessions.ts`

Create `frontend/src/lib/api/sessions.ts` — client-side functions for the W3-F1 endpoints:

```typescript
export interface QuizQuestionOut {
  question_id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  options?: Array<{ option_id: number; text: string }>;
}

export interface SessionRead {
  session_id: string;
  session_token: string;
  test_id: number;
  user_id: number;
  status: string;
  current_index: number;
  server_now: string;
  expires_at: string;
  first_question: QuizQuestionOut | null;
}

export interface AnswerResponse {
  session_id: string;
  question_id: string;
  question_index: number;
  score: number | null;
  algorithm: string;
  session_status: string;
  current_index: number;
  next_question: QuizQuestionOut | null;
}

/** Client-side: submit one answer and receive the next question. */
export async function submitAnswer(
  sessionId: string,
  questionId: string,
  submittedAnswers: (number | boolean | string)[],
): Promise<AnswerResponse> {
  const res = await fetch(`/api/v1/sessions/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, submitted_answers: submittedAnswers }),
  });
  if (!res.ok) throw new Error(`Answer submission failed: ${res.status}`);
  return res.json();
}
```

### 3. `TestRunner.tsx`

Create `frontend/src/app/take/[testId]/TestRunner.tsx` as `'use client'`:

- Props: `quizSession: SessionRead`, `user: AuthUser`
- Wraps children in `<AuthProvider user={user}>` so `useAuth()` works in subtree
- State:
  - `questions: QuizQuestionOut[]` — initialized with `[quizSession.first_question]`
  - `currentIndex: number` — starts at 0
  - `answers: Map<string, number[]>` — question_id → selected option indices
  - `submitting: boolean`
  - `completed: boolean`
- Answer handler: `(questionId, answer) => setAnswers(prev => new Map(prev).set(questionId, answer))`
- Previous: `setCurrentIndex(i => i - 1)` — disabled at index 0
- Next:
  - If `currentIndex + 1 < questions.length`: just `setCurrentIndex(i => i + 1)`
  - Else: call `submitAnswer(sessionId, currentQ.question_id, toArray(answers.get(currentQ.question_id)))` → append `next_question` to `questions`, increment index
  - If `session_status === 'SUBMITTED'` after submit: set `completed = true`
- Submit (on last question): same flow as "Next" but from last question; shows completed state
- Renders:
  - Loading/error states
  - `<QuestionCard>` for current question (reuse existing)
  - Prev/Next buttons
  - Answer count indicator
  - Completed state card

`toArray` helper: normalizes the `Map` value (could be `number | number[]`) to
`number[]` for the API call.

### 4. `page.tsx`

Create `frontend/src/app/take/[testId]/page.tsx` as async server component:

```tsx
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';
import { getSession } from '@/lib/session';
import TestRunner from './TestRunner';

const GATEWAY = process.env.API_GATEWAY_URL ?? 'http://api-gateway:8000';

export default async function TakePage({ params }: { params: Promise<{ testId: string }> }) {
  const { testId } = await params;
  const session = await getSession();
  if (!session) redirect('/');

  const jar = await cookies();
  const token = jar.get('auth_token')?.value ?? '';

  const res = await fetch(`${GATEWAY}/v1/api/sessions/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ test_id: Number(testId) }),
    cache: 'no-store',
  });

  if (!res.ok) {
    // Render inline error — do not throw (would trigger error boundary with no context)
    const msg = await res.text();
    return <ErrorCard message={msg} />;
  }

  const quizSession = await res.json();
  const user = { id: session.userId, email: session.email, role: session.role };

  return <TestRunner quizSession={quizSession} user={user} />;
}
```

Include a small inline `ErrorCard` component (or reuse a card pattern from the
dashboard) that shows the error message and a "Back" link.

---

## Test Plan

### `AuthContext.test.tsx`

Location: `frontend/src/__tests__/context/AuthContext.test.tsx`

- Renders children with `AuthProvider`; `useAuth()` returns the passed user object
- Verifies `id`, `email`, `role` values
- Throws (via `renderHook` outside provider) when `useAuth()` is used without `AuthProvider`

### `TestRunner.test.tsx`

Location: `frontend/src/__tests__/app/take/TestRunner.test.tsx`

Mock: `@/lib/api/sessions` → `submitAnswer` jest mock

Tests:
- Renders the `question_text` of `first_question`
- Previous button is disabled on first question
- Selecting an answer updates the `answers` Map (verify via aria state on question component)
- Next button calls `submitAnswer` and renders the returned `next_question`
- Completed state renders after `session_status === 'SUBMITTED'`

---

## Lint Plan

```bash
cd frontend && corepack enable && pnpm lint
```

Fix any ESLint errors that `--fix` cannot auto-resolve.

---

## Major Decisions

### Decision 1: Route placement — standalone vs. `(dashboard)` layout

**Options:**
- A. `app/take/[testId]/page.tsx` — standalone route outside `(dashboard)`, no
  sidebar/nav chrome (recommended)
- B. `app/(dashboard)/take/[testId]/page.tsx` — inside dashboard layout with nav

**Recommended: A.** The spec explicitly states `frontend/app/take/[testId]/page.tsx`.
Test-taking is a focused full-screen experience; the dashboard navigation is a
distraction during an exam. The brownfield page under `(dashboard)` is a different
feature with a different URL pattern.

### Decision 2: Question fetch strategy — pre-fetch vs. on-demand

**Options:**
- A. Pre-fetch all questions server-side (requires a bulk-fetch endpoint — doesn't exist)
- B. Lazy fetch via answer submission: first_question comes from session; next questions
  come from `POST /sessions/{id}/answer` (recommended)
- C. Add a new backend endpoint — out of scope for W3-F3

**Recommended: B.** Aligns with the existing backend API contract. Questions are
cached in the `questions` state array; `currentIndex` navigates the cache.

---

## Doc Updates

After implementation:
1. Check off all 5 steps in `docs/features/w3-f3-test-taking-frontend-skeleton.md`
2. Set status to `✅ Done` in `docs/FEATURE_STATUS.md`
3. Update `docs/index.md` status column for W3-F3
4. Write `docs/adr/w3-f3-test-taking-frontend-skeleton.md`
