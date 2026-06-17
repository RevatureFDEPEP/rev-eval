import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ScorePerAttemptChart } from '@/components/results/ScorePerAttemptChart';
import type { ReportAttemptItem } from '@/lib/api/types';

// recharts' ResponsiveContainer measures its parent, which is 0x0 in jsdom and
// renders nothing. Give it fixed dimensions so the chart (and the accessible
// figure wrapper) mount.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 600, height: 300 }}>{children}</div>
    ),
  };
});

const SCORED: ReportAttemptItem[] = [
  {
    session_id: 'a',
    test_id: 1,
    test_name: 'Algorithms',
    status: 'SUBMITTED',
    score: 0.8,
    correct_count: 8,
    total_answered: 10,
  },
];

describe('ScorePerAttemptChart', () => {
  it('renders an accessible figure when there is scored data', () => {
    render(<ScorePerAttemptChart attempts={SCORED} />);
    expect(screen.getByRole('img', { name: /score percentage per quiz attempt/i })).toBeInTheDocument();
  });

  it('shows an empty message when no attempt has a score', () => {
    render(
      <ScorePerAttemptChart attempts={[{ ...SCORED[0], score: null }]} />,
    );
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText(/no scored attempts yet/i)).toBeInTheDocument();
  });
});
