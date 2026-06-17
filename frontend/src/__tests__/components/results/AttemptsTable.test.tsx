import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AttemptsTable } from '@/components/results/AttemptsTable';
import type { ReportAttemptItem } from '@/lib/api/types';

const ATTEMPTS: ReportAttemptItem[] = [
  {
    session_id: 'feat',
    test_id: 5,
    test_name: 'Algorithms',
    status: 'SUBMITTED',
    score: 0.8,
    correct_count: 8,
    total_answered: 10,
    time_spent_seconds: 600,
    submitted_at: '2026-06-17T10:30:00Z',
  },
  {
    session_id: 'other',
    test_id: 6,
    test_name: null,
    status: 'EXPIRED',
    score: null,
    correct_count: 0,
    total_answered: 0,
    time_spent_seconds: null,
    submitted_at: null,
  },
];

describe('AttemptsTable', () => {
  it('renders one row per attempt with formatted cells', () => {
    render(<AttemptsTable attempts={ATTEMPTS} />);
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2
    expect(screen.getByText('Algorithms')).toBeInTheDocument();
    expect(screen.getByText('Test 6')).toBeInTheDocument(); // name fallback
    expect(screen.getByText('80%')).toBeInTheDocument();
    expect(screen.getByText('8/10')).toBeInTheDocument();
  });

  it('renders an em-dash for null score and time', () => {
    render(<AttemptsTable attempts={[ATTEMPTS[1]]} />);
    // null score, null time, null submitted_at all collapse to em-dash
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
  });

  it('marks the featured attempt with aria-current', () => {
    render(<AttemptsTable attempts={ATTEMPTS} featuredSessionId="feat" />);
    const featuredCell = screen.getByText('Algorithms');
    const row = featuredCell.closest('tr');
    expect(row).toHaveAttribute('aria-current', 'true');
    // the non-featured row is not marked
    const otherRow = screen.getByText('Test 6').closest('tr');
    expect(otherRow).not.toHaveAttribute('aria-current');
  });

  it('shows an empty state when there are no attempts', () => {
    render(<AttemptsTable attempts={[]} />);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText(/haven't completed any quizzes/i)).toBeInTheDocument();
  });

  it('shows the status as a badge', () => {
    render(<AttemptsTable attempts={ATTEMPTS} />);
    const featuredRow = screen.getByText('Algorithms').closest('tr')!;
    expect(within(featuredRow).getByText('SUBMITTED')).toBeInTheDocument();
  });
});
