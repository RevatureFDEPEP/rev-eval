import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { TestAggregateRow, TimeseriesPoint } from '@/lib/api/types';
import { PassRateBarChart } from './PassRateBarChart';
import { AttemptVolumeChart } from './AttemptVolumeChart';

// recharts' ResponsiveContainer needs a measured box; jsdom reports 0×0, so
// these assert the empty-state / chrome contracts rather than rendered SVG geometry.

describe('PassRateBarChart', () => {
  it('renders the EmptyState when there are no rows', () => {
    render(<PassRateBarChart rows={[]} passThreshold={70} />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText(/No submitted attempts yet/i)).toBeInTheDocument();
  });

  it('renders an accessible titled chart figure for non-empty data', () => {
    const rows: TestAggregateRow[] = [
      {
        test_id: 1,
        test_name: 'Java',
        total_attempts: 4,
        distinct_candidates: 3,
        avg_score: 65,
        pass_rate: 50,
        median_duration_seconds: 1200,
      },
    ];
    render(<PassRateBarChart rows={rows} passThreshold={70} />);
    expect(screen.getByRole('img', { name: /pass rate/i })).toBeInTheDocument();
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
  });
});

describe('AttemptVolumeChart', () => {
  it('renders the EmptyState when there are no points', () => {
    render(<AttemptVolumeChart points={[]} />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText(/No attempts in this range/i)).toBeInTheDocument();
  });

  it('renders an accessible titled chart figure for non-empty data', () => {
    const points: TimeseriesPoint[] = [
      { date: '2026-06-01', test_id: 1, test_name: 'Java', attempts: 2 },
    ];
    render(<AttemptVolumeChart points={points} />);
    expect(screen.getByRole('img', { name: /attempts per day/i })).toBeInTheDocument();
  });
});
