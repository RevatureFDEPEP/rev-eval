/**
 * /results/[sessionId] — Candidate Results Page (W4-F2).
 *
 * Async server component. Identity comes from the authenticated session
 * (the `auth_token` cookie via getSession), NOT from the route: W4-F1 is keyed
 * by user_id and exposes no per-session lookup (ADR 0001). `sessionId` selects
 * which attempt to feature; AttemptsRegion 404s if it is not the caller's.
 *
 * Three regions (summary, attempt table, score chart) each stream inside their
 * own Suspense boundary (R2) and per-region error boundary (R3); the page chrome
 * renders on first byte while the reporting data loads.
 */
import { Suspense } from 'react';
import { notFound, redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { ServerApiError, getCurrentUserServer } from '@/lib/api/server';
import { loadUserAttempts } from '@/lib/api/reports';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { RegionErrorBoundary } from '@/components/results/RegionErrorBoundary';
import { AttemptsRegion, ChartRegion, SummaryRegion } from './regions';
import { ChartSkeleton, SummarySkeleton, TableSkeleton } from './skeletons';

interface ResultsPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { sessionId } = await params;

  // Middleware already redirects unauthenticated users; this is defensive.
  const session = await getSession();
  if (!session) {
    redirect('/');
  }
  const userId = session.userId;

  // Identity seeding and the ownership fetch are independent — run concurrently.
  const userPromise = getCurrentUserServer();

  // Ownership check at the page level (a server component, with no client error
  // boundary above it) so notFound() reaches not-found.tsx the standard way.
  // Only 404 when we positively know the attempt is not the caller's: a fetch
  // failure leaves `attempts` null so the regions surface their own error panel
  // (the cache()-shared rejection re-throws inside each region) instead of a
  // misleading "not found".
  let attempts = null;
  try {
    attempts = await loadUserAttempts(userId);
  } catch (e) {
    if (e instanceof ServerApiError && e.status === 401) redirect('/');
    // other failures: fall through; regions render their own error state
  }
  if (attempts && !attempts.items.some((a) => a.session_id === sessionId)) {
    notFound();
  }

  // Seed AuthContext for client children (W3-F3 pattern); never throws.
  const user = await userPromise;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <AuthProvider user={user}>
        <div className="mx-auto max-w-5xl space-y-8">
          <header>
            <h1 className="text-2xl font-bold text-slate-900">Results</h1>
            <p className="text-sm text-slate-600">
              Your quiz performance across all attempts.
            </p>
          </header>

          <RegionErrorBoundary label="your results summary">
            <Suspense fallback={<SummarySkeleton />}>
              <SummaryRegion userId={userId} />
            </Suspense>
          </RegionErrorBoundary>

          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <RegionErrorBoundary label="your attempt history">
              <Suspense fallback={<TableSkeleton />}>
                <AttemptsRegion userId={userId} featuredSessionId={sessionId} />
              </Suspense>
            </RegionErrorBoundary>

            <RegionErrorBoundary label="the score chart">
              <Suspense fallback={<ChartSkeleton />}>
                <ChartRegion userId={userId} featuredSessionId={sessionId} />
              </Suspense>
            </RegionErrorBoundary>
          </div>
        </div>
      </AuthProvider>
    </main>
  );
}
