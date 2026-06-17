import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ResultsSummary } from '@/components/results/ResultsSummary';
import type { UserReportSummary } from '@/lib/api/types';

const FULL: UserReportSummary = {
  user_id: 2,
  total_attempts: 3,
  average_score: 0.7,
  best_score: 0.9,
  total_time_spent_seconds: 3661,
  most_recent_attempt: {
    session_id: 's1',
    test_id: 5,
    test_name: 'Algorithms',
    status: 'SUBMITTED',
    score: 0.8,
    correct_count: 8,
    total_answered: 10,
    time_spent_seconds: 600,
    submitted_at: '2026-06-17T10:30:00Z',
  },
};

describe('ResultsSummary', () => {
  it('renders the headline aggregates formatted for display', () => {
    render(<ResultsSummary summary={FULL} />);
    expect(screen.getByText('90%')).toBeInTheDocument(); // best
    expect(screen.getByText('70%')).toBeInTheDocument(); // average
    expect(screen.getByText('3')).toBeInTheDocument(); // attempts
    expect(screen.getByText('1h 1m')).toBeInTheDocument(); // time spent
  });

  it('summarizes the most recent attempt', () => {
    render(<ResultsSummary summary={FULL} />);
    expect(screen.getByText(/Algorithms/)).toBeInTheDocument();
    expect(screen.getByText(/Most recent/)).toBeInTheDocument();
  });

  it('degrades null scores to an em-dash rather than NaN%', () => {
    render(
      <ResultsSummary
        summary={{
          user_id: 2,
          total_attempts: 0,
          average_score: null,
          best_score: null,
          total_time_spent_seconds: 0,
          most_recent_attempt: null,
        }}
      />,
    );
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/No attempts recorded yet/)).toBeInTheDocument();
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});
