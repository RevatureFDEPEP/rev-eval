/**
 * Pass-rate-per-test bar chart for the trainer dashboard (W4-F4).
 *
 * Receives the server-fetched /reports/aggregate rows as a prop (no client
 * fetch) and renders pass rate (% of attempts at/above the configured
 * threshold) per test. Reuses the shared <ChartWrapper>.
 */
'use client';

import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from 'recharts';
import type { TestAggregateRow } from '@/lib/api/types';
import { EmptyState } from '@/components/ui/empty-state';
import { ChartWrapper, chartLegendProps, chartTooltipProps } from '@/components/charts/ChartWrapper';

interface PassRateBarChartProps {
  rows: TestAggregateRow[];
  passThreshold: number;
}

export function PassRateBarChart({ rows, passThreshold }: PassRateBarChartProps) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No submitted attempts yet"
        description="Once candidates submit tests, pass rates per test appear here. Adjust the filters above to widen the range."
      />
    );
  }

  const data = rows.map((r) => ({
    label: r.test_name,
    passRate: r.pass_rate ?? 0,
    attempts: r.total_attempts,
  }));

  return (
    <ChartWrapper
      title={`Pass rate per test (≥ ${passThreshold}%)`}
      ariaLabel={`Bar chart of pass rate across ${data.length} tests, threshold ${passThreshold} percent`}
    >
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} width={48} />
        <Tooltip {...chartTooltipProps} />
        <Legend {...chartLegendProps} />
        <Bar dataKey="passRate" name="Pass rate (%)" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartWrapper>
  );
}
