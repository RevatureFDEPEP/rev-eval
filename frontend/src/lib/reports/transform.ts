/**
 * Pure transforms for the trainer dashboard (W4-F4) — no React, so they unit
 * test directly. Parse URL search params into report filters and reshape the
 * /reports/timeseries rows for the recharts LineChart.
 */
import type { ReportFilters, TimeseriesPoint } from '@/lib/api/types';

type SearchParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/** Read `test_id`/`from`/`to` from URL search params into ReportFilters. */
export function parseReportFilters(searchParams: SearchParams): ReportFilters {
  const filters: ReportFilters = {};
  const testId = first(searchParams.test_id);
  if (testId !== undefined && testId !== '') {
    const n = Number(testId);
    if (Number.isInteger(n) && n > 0) filters.testId = n;
  }
  const from = first(searchParams.from);
  if (from) filters.from = from;
  const to = first(searchParams.to);
  if (to) filters.to = to;
  return filters;
}

/** Stable per-test series key for the multi-series line chart. */
export function seriesKey(testId: number): string {
  return `test_${testId}`;
}

export interface VolumeSeries {
  key: string;
  name: string;
}

export interface VolumePivot {
  /** One row per date: { date, [seriesKey]: attempts, total }. */
  rows: Array<Record<string, number | string>>;
  /** One entry per distinct test, ordered by test_id. */
  series: VolumeSeries[];
}

/**
 * Pivot (date, test) cells into per-date rows with one column per test plus a
 * summed `total`. Drives the line chart: one line per quiz, and a `total` line
 * that sums across tests. Filtering to a single test naturally yields one
 * series. Dates are sorted ascending; missing (date, test) cells read as 0.
 */
export function pivotVolumeByTest(points: TimeseriesPoint[]): VolumePivot {
  const seriesMap = new Map<number, string>();
  const byDate = new Map<string, Record<string, number | string>>();

  for (const p of points) {
    if (!seriesMap.has(p.test_id)) seriesMap.set(p.test_id, p.test_name);
    let row = byDate.get(p.date);
    if (!row) {
      row = { date: p.date, total: 0 };
      byDate.set(p.date, row);
    }
    row[seriesKey(p.test_id)] = (Number(row[seriesKey(p.test_id)]) || 0) + p.attempts;
    row.total = (Number(row.total) || 0) + p.attempts;
  }

  const series = [...seriesMap.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([testId, name]) => ({ key: seriesKey(testId), name }));

  // Backfill 0 for tests with no attempts on a given date, so lines are continuous.
  const rows = [...byDate.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
  for (const row of rows) {
    for (const s of series) {
      if (row[s.key] === undefined) row[s.key] = 0;
    }
  }

  return { rows, series };
}
