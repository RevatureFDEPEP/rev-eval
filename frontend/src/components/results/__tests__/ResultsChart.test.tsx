import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResultsChart from '../ResultsChart';
import type { UserSessionEntry } from '@/lib/api/types';

// recharts uses ResizeObserver internally — polyfill for jsdom
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

const makeAttempt = (overrides: Partial<UserSessionEntry> = {}): UserSessionEntry => ({
  session_id: 'sess1',
  test_id: 1,
  test_name: 'Test',
  status: 'COMPLETED',
  completed_at: '2026-06-01T10:00:00Z',
  percentage_score: 80,
  total_questions: 20,
  time_spent_seconds: 600,
  ...overrides,
});

describe('ResultsChart', () => {
  it('renders without crashing when given attempts', () => {
    const attempts = [
      makeAttempt({ session_id: 'a1', percentage_score: 85 }),
      makeAttempt({ session_id: 'b1', percentage_score: 55 }),
    ];

    const { container } = render(<ResultsChart attempts={attempts} />);
    expect(container.firstChild).not.toBeNull();
  });

  it('shows empty state when no attempts provided', () => {
    render(<ResultsChart attempts={[]} />);
    expect(screen.getByText(/no attempt data available/i)).toBeTruthy();
  });

  it('renders a container div for multiple attempts', () => {
    const attempts = [
      makeAttempt({ session_id: 'a1', percentage_score: 90 }),
      makeAttempt({ session_id: 'a2', percentage_score: 65 }),
      makeAttempt({ session_id: 'a3', percentage_score: 75 }),
    ];

    const { container } = render(<ResultsChart attempts={attempts} currentSessionId="a3" />);
    expect(container.firstChild).not.toBeNull();
  });

  it('handles missing percentage_score gracefully (defaults to 0)', () => {
    const attempts = [makeAttempt({ session_id: 'a1', percentage_score: undefined })];
    expect(() => render(<ResultsChart attempts={attempts} />)).not.toThrow();
  });

  it('highlights the current session when currentSessionId is provided', () => {
    const attempts = [
      makeAttempt({ session_id: 'current', percentage_score: 72 }),
      makeAttempt({ session_id: 'other', percentage_score: 60 }),
    ];
    expect(() =>
      render(<ResultsChart attempts={attempts} currentSessionId="current" />)
    ).not.toThrow();
  });

  it('matches numeric session_id against string currentSessionId (type coercion)', () => {
    // API returns session_id as a number; URL param is always a string.
    // String() normalisation must make these equal so the highlight works.
    const attempts = [
      makeAttempt({ session_id: 42 as unknown as string, percentage_score: 88 }),
      makeAttempt({ session_id: 43 as unknown as string, percentage_score: 55 }),
    ];
    expect(() =>
      render(<ResultsChart attempts={attempts} currentSessionId="42" />)
    ).not.toThrow();
  });
});
