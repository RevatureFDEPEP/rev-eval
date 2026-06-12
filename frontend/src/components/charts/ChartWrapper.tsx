/**
 * <ChartWrapper> — shared recharts shell (W4-F2, reused by W4-F4).
 *
 * Owns the cross-application chart contract: a ResponsiveContainer at a
 * consistent height, a visible title, and an accessible-name wrapper
 * (role="img" + aria-label). Chart-specific composition (BarChart, LineChart,
 * series, axes) is passed as the single recharts child; consumers pull
 * `chartTooltipProps` / `chartLegendProps` so tooltips and legends render
 * identically on every chart.
 */
'use client';

import type { ReactElement } from 'react';
import { ResponsiveContainer } from 'recharts';

/** Standard Tooltip styling — spread into every chart's <Tooltip>. */
export const chartTooltipProps = {
  cursor: { fill: 'var(--muted)', opacity: 0.4 },
  contentStyle: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    fontSize: '0.75rem',
    color: 'var(--card-foreground)',
  },
} as const;

/** Standard Legend styling — spread into every chart's <Legend>. */
export const chartLegendProps = {
  iconSize: 10,
  wrapperStyle: { fontSize: '0.75rem' },
} as const;

interface ChartWrapperProps {
  /** Visible heading rendered above the chart. */
  title: string;
  /** Accessible name describing what the visualization shows. */
  ariaLabel: string;
  /** Container height in px — consistent across the app unless overridden. */
  height?: number;
  /** A single recharts chart element (BarChart, LineChart, …). */
  children: ReactElement;
}

export function ChartWrapper({ title, ariaLabel, height = 320, children }: ChartWrapperProps) {
  return (
    <figure role="img" aria-label={ariaLabel} className="w-full">
      <figcaption className="mb-3 text-sm font-medium text-muted-foreground">
        {title}
      </figcaption>
      <div className="w-full" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
