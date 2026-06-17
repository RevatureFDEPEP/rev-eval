'use client';

/**
 * ScorePerAttemptChart (W4-F2).
 *
 * The spec offers "per-question time-on-task OR score-per-attempt"; W4-F1
 * exposes per-attempt data only, so this renders score-per-attempt — one bar
 * per scored attempt, oldest→newest, with the featured attempt accented. Built
 * on the shared <ChartWrapper>.
 */
import { Bar, Cell } from 'recharts';
import { ChartWrapper } from './ChartWrapper';
import { buildScoreSeries } from '@/lib/results/format';
import type { ReportAttemptItem } from '@/lib/api/types';

const FEATURED_FILL = '#2563eb'; // blue-600 — the attempt the page links to
const BASE_FILL = '#93c5fd'; // blue-300 — the rest of the history

export function ScorePerAttemptChart({
  attempts,
  featuredSessionId,
}: {
  attempts: ReportAttemptItem[];
  featuredSessionId?: string;
}) {
  const data = buildScoreSeries(attempts, featuredSessionId);

  if (data.length === 0) {
    return (
      <p className="flex h-[200px] items-center justify-center text-center text-sm text-slate-500">
        No scored attempts yet — complete a quiz to see your score trend.
      </p>
    );
  }

  return (
    <ChartWrapper
      ariaLabel="Bar chart of score percentage per quiz attempt, oldest to newest"
      data={data as unknown as Array<Record<string, unknown>>}
      xKey="label"
      yDomain={[0, 100]}
      yTickFormatter={(v) => `${v}%`}
      tooltipFormatter={(v) => [`${v}%`, 'Score']}
    >
      <Bar dataKey="scorePct" name="Score %" radius={[4, 4, 0, 0]}>
        {data.map((point) => (
          <Cell
            key={point.sessionId}
            fill={point.featured ? FEATURED_FILL : BASE_FILL}
          />
        ))}
      </Bar>
    </ChartWrapper>
  );
}
