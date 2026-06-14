import { notFound, redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { mintSessionServer, ServerApiError } from '@/lib/api/server';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { TestRunner } from '@/components/take/TestRunner';

/**
 * /take/[testId] — async server component (W3-F3).
 *
 * Guards the session, mints a quiz session server-side, and seeds both the
 * first (sanitized) question and the candidate's display identity into the
 * initial HTML — no client spinner, and the raw auth cookie never reaches the
 * bundle. The interactive sequential-reveal flow lives in <TestRunner>.
 */
export default async function TakeTestPage({
  params,
}: {
  params: Promise<{ testId: string }>;
}) {
  const { testId } = await params;
  const id = Number(testId);
  if (!Number.isInteger(id) || id <= 0) notFound();

  const session = await getSession();
  if (!session) redirect('/');

  let minted;
  try {
    minted = await mintSessionServer(id);
  } catch (err) {
    if (err instanceof ServerApiError) {
      if (err.status === 401) redirect('/');
      if (err.status === 404) notFound();
    }
    // 422 (empty bank), 502 (question service down), etc. → error boundary.
    throw err;
  }

  const identity = {
    userId: session.userId,
    email: session.email,
    role: session.role,
  };

  return (
    <AuthProvider identity={identity}>
      <TestRunner session={minted} />
    </AuthProvider>
  );
}
