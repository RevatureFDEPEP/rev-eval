/**
 * Attempt-volume-over-time line chart for the trainer dashboard (W4-F4).
 *
 * Receives the server-fetched /reports/timeseries cells as a prop. Pivots them
 * (pure pivotVolumeByTest) into per-date rows: an emphasized "Total" line
 * (sum across tests) plus one line per quiz. When a single test is selected via
 * the filter, the API returns only that test, so the chart naturally shows one
 * series. Reuses the shared <ChartWrapper>.
 */
'use client';

import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts';
import type { TimeseriesPoint } from '@/lib/api/types';
import { pivotVolumeByTest } from '@/lib/reports/transform';
import { EmptyState } from '@/components/ui/empty-state';
import { ChartWrapper, chartLegendProps, chartTooltipProps } from '@/components/charts/ChartWrapper';

interface AttemptVolumeChartProps {
  points: TimeseriesPoint[];
}

// Recharts-friendly palette cycling for the per-quiz lines.
const SERIES_COLORS = ['var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)'];

export function AttemptVolumeChart({ points }: AttemptVolumeChartProps) {
  if (points.length === 0) {
    return (
      <EmptyState
        title="No attempts in this range"
        description="Submitted attempts appear here grouped by day. Widen the date range or clear the test filter to see more."
      />
    );
  }

  const { rows, series } = pivotVolumeByTest(points);
  const multiTest = series.length > 1;

  return (
    <ChartWrapper
      title="Attempt volume over time"
      ariaLabel={`Line chart of submitted attempts per day across ${series.length} test${
        multiTest ? 's' : ''
      }`}
    >
      <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
        <Tooltip {...chartTooltipProps} />
        <Legend {...chartLegendProps} />
        {/* Total line only adds signal when more than one quiz is in view. */}
        {multiTest && (
          <Line
            type="monotone"
            dataKey="total"
            name="All tests"
            stroke="var(--chart-1)"
            strokeWidth={2}
            dot={false}
          />
        )}
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
            strokeWidth={multiTest ? 1.5 : 2}
            dot={false}
          />
        ))}
      </LineChart>
    </ChartWrapper>
  );
}
