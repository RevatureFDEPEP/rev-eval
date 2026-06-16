import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResultsChart from '../ResultsChart';
import type { GradedQuizQuestion } from '@/lib/api/types';

// recharts uses ResizeObserver internally — polyfill for jsdom
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

const makeQuestion = (overrides: Partial<GradedQuizQuestion> = {}): GradedQuizQuestion => ({
  question_id: 'q1',
  question_text: 'What is 2+2?',
  question_type: 'mcq',
  difficulty: 'easy',
  is_correct: true,
  time_spent_seconds: 30,
  ...overrides,
});

describe('ResultsChart', () => {
  it('renders without crashing when given questions', () => {
    const partA = [makeQuestion({ question_id: 'a1', is_correct: true, time_spent_seconds: 20 })];
    const partB = [makeQuestion({ question_id: 'b1', is_correct: false, time_spent_seconds: 45 })];

    const { container } = render(<ResultsChart partA={partA} partB={partB} />);
    expect(container.firstChild).not.toBeNull();
  });

  it('shows empty state when no questions provided', () => {
    render(<ResultsChart partA={[]} partB={[]} />);
    expect(screen.getByText(/no question-level data available/i)).toBeTruthy();
  });

  it('renders a container div for combined part A + B questions', () => {
    const partA = [
      makeQuestion({ question_id: 'a1', is_correct: true, time_spent_seconds: 10 }),
      makeQuestion({ question_id: 'a2', is_correct: false, time_spent_seconds: 25 }),
    ];
    const partB = [
      makeQuestion({ question_id: 'b1', is_correct: true, time_spent_seconds: 15 }),
    ];

    // ResponsiveContainer renders a div wrapper in jsdom (no SVG — zero dimensions)
    const { container } = render(<ResultsChart partA={partA} partB={partB} />);
    expect(container.firstChild).not.toBeNull();
  });

  it('handles missing time_spent_seconds gracefully (defaults to 1)', () => {
    const partA = [makeQuestion({ question_id: 'a1', time_spent_seconds: undefined })];
    expect(() => render(<ResultsChart partA={partA} partB={[]} />)).not.toThrow();
  });

  it('handles missing is_correct gracefully (defaults to false)', () => {
    const partA = [makeQuestion({ question_id: 'a1', is_correct: undefined })];
    expect(() => render(<ResultsChart partA={partA} partB={[]} />)).not.toThrow();
  });
});
