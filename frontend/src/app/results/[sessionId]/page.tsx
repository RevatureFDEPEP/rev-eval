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
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';
import { getCurrentUserServer } from '@/lib/api/server';
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

  // Seed AuthContext for client children (W3-F3 pattern); never throws.
  const user = await getCurrentUserServer();

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
