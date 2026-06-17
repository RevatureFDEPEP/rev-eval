'use client';

/**
 * ChartWrapper (W4-F2, reused by W4-F4).
 *
 * The single place the app standardizes a bar chart: it owns recharts'
 * ResponsiveContainer at a consistent height, a standard Tooltip and Legend,
 * grid + axes, and — for accessibility — wraps the canvas in a `role="img"`
 * figure carrying an `aria-label` (recharts' SVG is otherwise opaque to screen
 * readers). Callers supply the data and the `<Bar>` series as children, so the
 * same wrapper renders a single-series score chart here and the multi-series
 * trainer charts in W4-F4.
 */
import type { ReactNode } from 'react';
import {
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface ChartWrapperProps {
  /** Screen-reader description of the chart (required — the SVG is opaque). */
  ariaLabel: string;
  /** Row objects; each key is addressable by `xKey` / the series `dataKey`. */
  data: object[];
  /** Row key used for the category (X) axis. */
  xKey: string;
  /** The `<Bar>` series (one or more). */
  children: ReactNode;
  /** Fixed pixel height; width is always responsive. */
  height?: number;
  /** Optional fixed Y domain, e.g. `[0, 100]` for percentages. */
  yDomain?: [number, number];
  yTickFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number, name: string) => [string, string];
}

const DEFAULT_HEIGHT = 280;

export function ChartWrapper({
  ariaLabel,
  data,
  xKey,
  children,
  height = DEFAULT_HEIGHT,
  yDomain,
  yTickFormatter,
  tooltipFormatter,
}: ChartWrapperProps) {
  return (
    <figure role="img" aria-label={ariaLabel} className="m-0 w-full">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: '#475569' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={yDomain}
            tick={{ fontSize: 12, fill: '#475569' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={yTickFormatter}
            width={44}
          />
          <Tooltip formatter={tooltipFormatter} cursor={{ fill: '#f1f5f9' }} />
          <Legend />
          {children}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}
