/**
 * Streaming server regions for the results page (W4-F2).
 *
 * Each region fetches its own slice and is rendered inside its own
 * <Suspense> + <RegionErrorBoundary> on the page, so they stream independently
 * and one region's failure blanks only its panel (R3). The summary and the
 * attempts share no fetch; the table and chart both read attempts, de-duped by
 * the React cache() loaders so it is one round-trip per render.
 *
 * Ownership lives here, in AttemptsRegion: once the caller's attempts load, a
 * `featuredSessionId` that is not among them is positively not theirs, so we
 * `notFound()`. The boundary re-throws that control-flow error, so it reaches
 * the route's not-found UI rather than the per-region error panel.
 */
import { notFound } from 'next/navigation';
import { AttemptsTable } from '@/components/results/AttemptsTable';
import { ResultsSummary } from '@/components/results/ResultsSummary';
import { ScorePerAttemptChart } from '@/components/results/ScorePerAttemptChart';
import { loadUserAttempts, loadUserSummary } from '@/lib/api/reports';

export async function SummaryRegion({ userId }: { userId: number }) {
  const summary = await loadUserSummary(userId);
  return <ResultsSummary summary={summary} />;
}

export async function AttemptsRegion({
  userId,
  featuredSessionId,
}: {
  userId: number;
  featuredSessionId: string;
}) {
  const attempts = await loadUserAttempts(userId);
  if (!attempts.items.some((a) => a.session_id === featuredSessionId)) {
    notFound();
  }
  return (
    <AttemptsTable attempts={attempts.items} featuredSessionId={featuredSessionId} />
  );
}

export async function ChartRegion({
  userId,
  featuredSessionId,
}: {
  userId: number;
  featuredSessionId: string;
}) {
  const attempts = await loadUserAttempts(userId);
  return (
    <section aria-labelledby="chart-heading" className="space-y-3">
      <h2 id="chart-heading" className="text-lg font-semibold text-slate-900">
        Score trend
      </h2>
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <ScorePerAttemptChart
          attempts={attempts.items}
          featuredSessionId={featuredSessionId}
        />
      </div>
    </section>
  );
}
