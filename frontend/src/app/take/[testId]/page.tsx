/**
 * /take/[testId] — test-taking page (W3-F3 skeleton).
 *
 * Async server component: reads the httpOnly `auth_token` cookie, mints a quiz
 * session and fetches the display identity server-side (via the gateway), then
 * hands the session to the <TestRunner> client component wrapped in <AuthProvider>.
 * Because the session (and its first question) is fetched on the server, the
 * first question is present in the initial HTML — no client loading spinner.
 */
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getIdentityServer, mintSessionServer } from '@/lib/api/server';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { TestRunner } from '@/components/take/TestRunner';

interface TakePageProps {
  params: Promise<{ testId: string }>;
}

export default async function TakePage({ params }: TakePageProps) {
  const { testId } = await params;

  // Gate on the cookie before hitting the gateway; unauthenticated → login.
  const session = await getSession();
  if (!session) {
    redirect('/');
  }

  const testIdNum = Number.parseInt(testId, 10);
  if (Number.isNaN(testIdNum)) {
    redirect('/');
  }

  // Server-side mint + identity: the first question lands in the initial HTML
  // and only the derived identity (not the cookie) crosses to the client.
  const [quizSession, identity] = await Promise.all([
    mintSessionServer(testIdNum),
    getIdentityServer(),
  ]);

  return (
    <AuthProvider initialUser={identity}>
      <TestRunner session={quizSession} />
    </AuthProvider>
  );
}
