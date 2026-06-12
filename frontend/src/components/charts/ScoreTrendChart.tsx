/**
 * Score-per-attempt bar chart for the candidate results page (W4-F2).
 *
 * Receives the server-fetched attempt history as a prop (no client fetch) and
 * renders scored attempts chronologically. The attempt matching the current
 * /results/[sessionId] route is emphasized with the secondary chart color.
 */
'use client';

import { Bar, BarChart, CartesianGrid, Cell, Legend, Tooltip, XAxis, YAxis } from 'recharts';
import type { ReportAttemptItem } from '@/lib/api/types';
import { ChartWrapper, chartLegendProps, chartTooltipProps } from './ChartWrapper';

interface ScoreTrendChartProps {
  attempts: ReportAttemptItem[];
  /** Session highlighted as “this attempt” (the route param). */
  highlightSessionId?: string;
}

interface ChartDatum {
  sessionId: string;
  label: string;
  score: number;
}

function toChartData(attempts: ReportAttemptItem[]): ChartDatum[] {
  return attempts
    .filter((a) => a.score !== null && a.submitted_at !== null)
    .sort((a, b) => (a.submitted_at as string).localeCompare(b.submitted_at as string))
    .map((a) => ({
      sessionId: a.session_id,
      label: `${a.test_name} · ${new Date(a.submitted_at as string).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })}`,
      score: Math.round((a.score as number) * 10) / 10,
    }));
}

export function ScoreTrendChart({ attempts, highlightSessionId }: ScoreTrendChartProps) {
  const data = toChartData(attempts);

  if (data.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No scored attempts yet — submit a test to see your score trend.
      </p>
    );
  }

  return (
    <ChartWrapper
      title="Score per attempt"
      ariaLabel={`Bar chart of scores across ${data.length} submitted attempts, most recent last`}
    >
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} width={48} />
        <Tooltip {...chartTooltipProps} />
        <Legend {...chartLegendProps} />
        <Bar dataKey="score" name="Score (%)" fill="var(--chart-1)" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.sessionId}
              fill={d.sessionId === highlightSessionId ? 'var(--chart-2)' : 'var(--chart-1)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ChartWrapper>
  );
}
