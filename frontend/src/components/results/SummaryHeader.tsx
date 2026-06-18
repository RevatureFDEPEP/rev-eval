import { Award, ClipboardList, Clock, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { UserReportSummary } from '@/lib/api/types';
import { formatDuration, formatScore } from '@/lib/utils/format';

interface SummaryHeaderProps {
  summary: UserReportSummary;
}

interface Stat {
  label: string;
  value: string;
  icon: typeof Award;
  hint?: string;
}

/**
 * Headline summary region: the participant's score and elapsed time at a
 * glance, plus supporting aggregates from the report envelope.
 */
export function SummaryHeader({ summary }: SummaryHeaderProps) {
  const stats: Stat[] = [
    {
      label: 'Best score',
      value: formatScore(summary.best_score),
      icon: Award,
      hint: 'Highest across all attempts',
    },
    {
      label: 'Average score',
      value: formatScore(summary.average_score),
      icon: Target,
      hint: `Across ${summary.total_attempts} attempt${
        summary.total_attempts === 1 ? '' : 's'
      }`,
    },
    {
      label: 'Time on task',
      value: formatDuration(summary.total_time_spent),
      icon: Clock,
      hint: 'Total time spent',
    },
    {
      label: 'Attempts',
      value: String(summary.total_attempts),
      icon: ClipboardList,
      hint: 'Sessions completed',
    },
  ];

  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Your results
        </p>
        <h1 className="text-3xl font-semibold text-slate-900">Performance summary</h1>
        <p className="max-w-2xl text-sm text-slate-500">
          A breakdown of how you&apos;ve done across your quiz attempts.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, hint }) => (
          <Card key={label} className="border border-slate-200 bg-white/95 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">{label}</CardTitle>
              <Icon className="h-4 w-4 text-orange-400" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold text-slate-900">{value}</div>
              {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
