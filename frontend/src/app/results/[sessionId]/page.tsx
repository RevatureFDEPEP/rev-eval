import { Suspense } from 'react';
import { redirect } from 'next/navigation';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { AttemptsTable } from '@/components/results/AttemptsTable';
import { ChartWrapper } from '@/components/results/ChartWrapper';
import { SectionErrorBoundary } from '@/components/results/SectionErrorBoundary';
import { SectionErrorFallback } from '@/components/results/SectionErrorFallback';
import { SummaryHeader } from '@/components/results/SummaryHeader';
import {
  getUserAttemptsServer,
  getUserReportSummaryServer,
} from '@/lib/api/server';
import { getSession } from '@/lib/session';
import {
  AttemptsTableSkeleton,
  ChartSkeleton,
  SummarySkeleton,
} from './loading';

interface ResultsPageProps {
  params: Promise<{ sessionId: string }>;
}

/**
 * Results detail view for a finished quiz session.
 *
 * Server component: resolves the signed-in user from the `auth_token` cookie
 * (via getSession, which reads next/headers) and fetches the reporting
 * envelope server-side. Each data region streams in behind its own Suspense
 * boundary so one failing panel doesn't take down the page.
 *
 * Error isolation is two-part, because a throw inside an async server
 * component does NOT reach a client error boundary — it unwinds to the route
 * error.tsx. So each region try/catches its own server-side fetch and renders
 * SectionErrorFallback inline (handles a reporting 500), while
 * SectionErrorBoundary wraps the region for client-side render errors.
 */
export default async function ResultsPage({ params }: ResultsPageProps) {
  const { sessionId } = await params;
  const session = await getSession();
  if (!session) {
    redirect('/');
  }
  const userId = session.userId;

  return (
    <main className="mx-auto w-full max-w-6xl space-y-8 p-4 sm:p-6 lg:p-8">
      {/* Region 1 — headline summary (score + elapsed) */}
      <SectionErrorBoundary title="summary">
        <Suspense fallback={<SummarySkeleton />}>
          <SummaryRegion userId={userId} />
        </Suspense>
      </SectionErrorBoundary>

      {/* Regions 2 & 3 — single column on mobile, two columns on desktop */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionErrorBoundary title="attempts">
          <Suspense fallback={<AttemptsTableSkeleton />}>
            <AttemptsTableRegion userId={userId} sessionId={sessionId} />
          </Suspense>
        </SectionErrorBoundary>

        <SectionErrorBoundary title="chart">
          <Suspense fallback={<ChartSkeleton />}>
            <ChartRegion userId={userId} />
          </Suspense>
        </SectionErrorBoundary>
      </div>
    </main>
  );
}

/** Fetches the summary envelope and renders the headline. */
async function SummaryRegion({ userId }: { userId: number }) {
  let summary;
  try {
    summary = await getUserReportSummaryServer(userId);
  } catch (error) {
    console.error('Failed to load results summary:', error);
    return <SectionErrorFallback title="summary" />;
  }
  return <SummaryHeader summary={summary} />;
}

/** Fetches attempts and renders the per-attempt breakdown table. */
async function AttemptsTableRegion({
  userId,
  sessionId,
}: {
  userId: number;
  sessionId: string;
}) {
  let items;
  try {
    ({ items } = await getUserAttemptsServer(userId));
  } catch (error) {
    console.error('Failed to load attempts table:', error);
    return <SectionErrorFallback title="attempt breakdown" />;
  }
  return (
    <Card className="border border-slate-200">
      <CardHeader>
        <CardTitle>Attempt breakdown</CardTitle>
        <CardDescription>One row per attempt — result and time on task.</CardDescription>
      </CardHeader>
      <CardContent>
        <AttemptsTable attempts={items} highlightSessionId={sessionId} />
      </CardContent>
    </Card>
  );
}

/** Fetches attempts and renders the score-per-attempt chart. */
async function ChartRegion({ userId }: { userId: number }) {
  let items;
  try {
    ({ items } = await getUserAttemptsServer(userId));
  } catch (error) {
    console.error('Failed to load results chart:', error);
    return <SectionErrorFallback title="chart" />;
  }
  return (
    <Card className="border border-slate-200">
      <CardHeader>
        <CardTitle>Score over attempts</CardTitle>
        <CardDescription>How your score has trended across attempts.</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper attempts={items} />
      </CardContent>
    </Card>
  );
}
