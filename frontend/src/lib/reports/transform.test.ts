import { describe, expect, it } from 'vitest';
import type { TimeseriesPoint } from '@/lib/api/types';
import { parseReportFilters, pivotVolumeByTest, seriesKey } from './transform';

describe('parseReportFilters', () => {
  it('reads test_id/from/to', () => {
    expect(parseReportFilters({ test_id: '3', from: '2026-06-01', to: '2026-06-30' })).toEqual({
      testId: 3,
      from: '2026-06-01',
      to: '2026-06-30',
    });
  });

  it('ignores empty / non-positive / non-integer test_id', () => {
    expect(parseReportFilters({ test_id: '' })).toEqual({});
    expect(parseReportFilters({ test_id: '0' })).toEqual({});
    expect(parseReportFilters({ test_id: 'abc' })).toEqual({});
  });

  it('takes the first value when a param repeats', () => {
    expect(parseReportFilters({ test_id: ['2', '5'] })).toEqual({ testId: 2 });
  });

  it('returns empty filters for no params', () => {
    expect(parseReportFilters({})).toEqual({});
  });
});

const POINTS: TimeseriesPoint[] = [
  { date: '2026-06-01', test_id: 1, test_name: 'Java', attempts: 2 },
  { date: '2026-06-01', test_id: 2, test_name: 'Python', attempts: 1 },
  { date: '2026-06-02', test_id: 1, test_name: 'Java', attempts: 3 },
];

describe('pivotVolumeByTest', () => {
  it('pivots to per-date rows with a per-test column and a total', () => {
    const { rows, series } = pivotVolumeByTest(POINTS);

    expect(series).toEqual([
      { key: 'test_1', name: 'Java' },
      { key: 'test_2', name: 'Python' },
    ]);
    // 06-01: Java 2 + Python 1 = 3 total; 06-02: Java 3, Python backfilled 0.
    expect(rows).toEqual([
      { date: '2026-06-01', total: 3, test_1: 2, test_2: 1 },
      { date: '2026-06-02', total: 3, test_1: 3, test_2: 0 },
    ]);
  });

  it('sorts rows by date ascending', () => {
    const { rows } = pivotVolumeByTest([...POINTS].reverse());
    expect(rows.map((r) => r.date)).toEqual(['2026-06-01', '2026-06-02']);
  });

  it('collapses to a single series when one test is present (filtered view)', () => {
    const single = POINTS.filter((p) => p.test_id === 1);
    const { series, rows } = pivotVolumeByTest(single);
    expect(series).toEqual([{ key: seriesKey(1), name: 'Java' }]);
    expect(rows.every((r) => r.total === r.test_1)).toBe(true);
  });

  it('returns no rows/series for empty input', () => {
    expect(pivotVolumeByTest([])).toEqual({ rows: [], series: [] });
  });
});
