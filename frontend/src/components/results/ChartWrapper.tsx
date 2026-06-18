'use client';

import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Attempt } from '@/lib/api/types';
import { formatDuration } from '@/lib/utils/format';

interface ChartWrapperProps {
  /** Attempts from the server component, oldest-first. */
  attempts: Attempt[];
  /** Fixed chart height in pixels — keeps every results chart consistent. */
  height?: number;
}

interface ChartDatum {
  label: string;
  score: number;
  timeSpent: number;
}

const ACCENT = '#fb923c';

/**
 * Reusable bar-chart wrapper around recharts' ResponsiveContainer.
 *
 * Provides a consistent height, a standard Tooltip + Legend, and an
 * `aria-label` on the container so the chart is announced to assistive tech.
 * Renders score-per-attempt (with time-on-task in the tooltip) from the
 * attempts passed down by the server component.
 */
export function ChartWrapper({ attempts, height = 300 }: ChartWrapperProps) {
  const data = useMemo<ChartDatum[]>(
    () =>
      attempts.map((attempt, index) => ({
        label: `#${index + 1}`,
        score: Math.round(attempt.score),
        timeSpent: attempt.time_spent_seconds,
      })),
    [attempts],
  );

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500"
        style={{ height }}
      >
        No attempts to chart yet.
      </div>
    );
  }

  return (
    <div
      role="img"
      aria-label={`Bar chart of scores across ${data.length} attempt${
        data.length === 1 ? '' : 's'
      }`}
      style={{ width: '100%', height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
          <Tooltip
            formatter={(value: number, name: string) =>
              name === 'score'
                ? [`${value}%`, 'Score']
                : [formatDuration(value), 'Time on task']
            }
            labelFormatter={(label: string) => `Attempt ${label}`}
          />
          <Legend />
          <Bar
            dataKey="score"
            name="Score"
            fill={ACCENT}
            radius={[4, 4, 0, 0]}
            maxBarSize={48}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
