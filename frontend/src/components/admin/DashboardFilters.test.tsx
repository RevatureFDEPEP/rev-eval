import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardFilters } from './DashboardFilters';

// Stub the App Router so URL writes are observable; searchParams starts empty.
const replace = vi.fn();
let currentParams = new URLSearchParams('');
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => currentParams,
}));

const TESTS = [
  { id: 1, name: 'Java Fundamentals' },
  { id: 2, name: 'Python Data Structures' },
];

beforeEach(() => {
  vi.useFakeTimers();
  replace.mockReset();
  currentParams = new URLSearchParams('');
});
afterEach(() => vi.useRealTimers());

describe('DashboardFilters', () => {
  it('debounces date input: writes ?from= once after 300ms', () => {
    render(<DashboardFilters tests={TESTS} />);
    const from = screen.getByLabelText('From');

    fireEvent.change(from, { target: { value: '2026-06-01' } });
    expect(replace).not.toHaveBeenCalled(); // debounced, not immediate

    vi.advanceTimersByTime(300);
    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith('?from=2026-06-01', { scroll: false });
  });

  it('coalesces rapid date edits into a single navigation', () => {
    render(<DashboardFilters tests={TESTS} />);
    const to = screen.getByLabelText('To');

    fireEvent.change(to, { target: { value: '2026-06-10' } });
    fireEvent.change(to, { target: { value: '2026-06-20' } });
    vi.advanceTimersByTime(300);

    expect(replace).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith('?to=2026-06-20', { scroll: false });
  });

  it('reflects the current filters from the URL', () => {
    currentParams = new URLSearchParams('from=2026-06-05');
    render(<DashboardFilters tests={TESTS} />);
    expect((screen.getByLabelText('From') as HTMLInputElement).value).toBe('2026-06-05');
  });
});
