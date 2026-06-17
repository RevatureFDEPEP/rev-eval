/**
 * Route-level loading skeleton (W4-F2, R2).
 *
 * Shown while the page's own awaits resolve (session + identity), before the
 * regions begin streaming. Mirrors the final three-region layout so the page
 * does not visibly reflow when content arrives.
 */
import { ChartSkeleton, SummarySkeleton, TableSkeleton } from './skeletons';

export default function ResultsLoading() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="space-y-2">
          <div className="h-7 w-32 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-64 animate-pulse rounded bg-slate-200" />
        </header>
        <SummarySkeleton />
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <TableSkeleton />
          <ChartSkeleton />
        </div>
      </div>
    </main>
  );
}
