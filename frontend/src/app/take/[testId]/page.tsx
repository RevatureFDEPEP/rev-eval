/**
 * /take/[testId] — Test-taking page (W3-F3).
 *
 * Async server component: reads the auth cookie, mints a quiz session
 * server-side (POST /v1/api/sessions), and renders the first question in the
 * initial HTML — no client spinner. Interactive navigation is owned by the
 * client <TestRunner>.
 */

import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import {
  createSessionServer,
  getCurrentUserServer,
  ServerApiError,
} from '@/lib/api/server';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { TestRunner } from '@/components/quiz/TestRunner';
import { SessionResponse } from '@/lib/api/types';

interface TakeTestPageProps {
  params: Promise<{ testId: string }>;
}

/** Gateway status → participant-facing copy for session-mint failures. */
const SESSION_ERROR_MESSAGES: Record<number, string> = {
  400: 'This test is not a quiz.',
  403: 'This quiz is only available to participants.',
  404: "We couldn't find that test.",
  409: "This quiz doesn't have enough questions yet. Please contact your trainer.",
};

function TakeError({ title, message }: { title: string; message: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="max-w-md space-y-2 text-center">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        <p className="text-sm text-slate-600">{message}</p>
      </div>
    </main>
  );
}

export default async function TakeTestPage({ params }: TakeTestPageProps) {
  const { testId: testIdParam } = await params;
  const testId = Number(testIdParam);

  if (!Number.isInteger(testId) || testId <= 0) {
    return (
      <TakeError
        title="Invalid test"
        message="That test link doesn't look right. Please return to your dashboard and try again."
      />
    );
  }

  // Middleware already redirects unauthenticated users; this is defensive.
  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  // Identity and session both hit the gateway and are independent — fetch
  // concurrently. getCurrentUserServer resolves to null on failure (never
  // rejects), so a floating promise on the error path below is harmless.
  const userPromise = getCurrentUserServer();

  let quizSession: SessionResponse;
  try {
    quizSession = await createSessionServer(testId);
  } catch (e) {
    if (e instanceof ServerApiError) {
      if (e.status === 401) redirect('/');
      const message =
        SESSION_ERROR_MESSAGES[e.status] ??
        'The quiz service is temporarily unavailable. Please try again shortly.';
      return <TakeError title="Unable to start quiz" message={message} />;
    }
    throw e;
  }

  const user = await userPromise;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <AuthProvider user={user}>
        <TestRunner session={quizSession} />
      </AuthProvider>
    </main>
  );
}
