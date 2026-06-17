import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { useAutosave } from './useAutosave';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const answersOf = (entries: [string, number[]][]) => new Map(entries);

describe('useAutosave', () => {
  it('debounces and fires saveFn once after the interval with the full map', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    const answers = answersOf([
      ['q1', [1]],
      ['q2', [2, 3]],
    ]);
    renderHook(() => useAutosave('sess-1', answers, true, 1000, saveFn));

    expect(saveFn).not.toHaveBeenCalled();
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);
    expect(saveFn).toHaveBeenCalledWith('sess-1', { q1: [1], q2: [2, 3] });
  });

  it('does not fire while disabled', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    renderHook(() => useAutosave('sess-1', answersOf([['q1', [1]]]), false, 1000, saveFn));
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    expect(saveFn).not.toHaveBeenCalled();
  });

  it('does not fire for an empty answer map', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    renderHook(() => useAutosave('sess-1', answersOf([]), true, 1000, saveFn));
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(saveFn).not.toHaveBeenCalled();
  });

  it('reports "saved" on success', async () => {
    // Real timers here: waitFor polls on wall-clock, which fake timers freeze.
    vi.useRealTimers();
    const okFn = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useAutosave('sess-1', answersOf([['q1', [1]]]), true, 10, okFn),
    );
    await waitFor(() => expect(result.current).toBe('saved'));
  });

  it('halts permanently after a terminal 409 (no further PATCH)', async () => {
    const saveFn = vi.fn().mockRejectedValue(new ApiError(409, 'conflict', ''));
    const initial = answersOf([['q1', [1]]]);
    const { rerender } = renderHook(
      ({ answers }) => useAutosave('sess-1', answers, true, 1000, saveFn),
      { initialProps: { answers: initial } },
    );
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);

    // A further answer change must NOT trigger another save once halted.
    rerender({ answers: answersOf([['q1', [2]]]) });
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);
  });
});
