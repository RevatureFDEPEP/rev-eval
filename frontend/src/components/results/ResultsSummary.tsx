/**
 * ResultsSummary (W4-F2) — the headline region of the results page.
 *
 * Presentational (no client hooks) so it streams from the server. Shows the
 * candidate's headline score and elapsed time plus supporting aggregates from
 * the W4-F1 summary envelope. Scores are null until an attempt has answers, so
 * every figure degrades to an em-dash rather than rendering "NaN%".
 */
import { Card, CardContent } from '@/components/ui/card';
import {
  formatDateTime,
  formatDuration,
  formatScorePct,
} from '@/lib/results/format';
import type { UserReportSummary } from '@/lib/api/types';

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      </CardContent>
    </Card>
  );
}

export function ResultsSummary({ summary }: { summary: UserReportSummary }) {
  const recent = summary.most_recent_attempt;
  return (
    <section aria-labelledby="results-summary-heading" className="space-y-4">
      <div>
        <h2
          id="results-summary-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Your results
        </h2>
        {recent ? (
          <p className="text-sm text-slate-600">
            Most recent: {recent.test_name ?? `Test ${recent.test_id}`} —{' '}
            {formatScorePct(recent.score)} in {formatDuration(recent.time_spent_seconds)}{' '}
            ({formatDateTime(recent.submitted_at)})
          </p>
        ) : (
          <p className="text-sm text-slate-600">No attempts recorded yet.</p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Best score" value={formatScorePct(summary.best_score)} />
        <Stat label="Average score" value={formatScorePct(summary.average_score)} />
        <Stat label="Total attempts" value={String(summary.total_attempts)} />
        <Stat
          label="Time spent"
          value={formatDuration(summary.total_time_spent_seconds)}
        />
      </div>
    </section>
  );
}
