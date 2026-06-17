import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useServerTimer } from './useServerTimer';

// Anchor the wall clock so deadline math is deterministic.
const T0 = 1_750_000_000_000;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(T0);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useServerTimer', () => {
  it('decrements once per second from the server-anchored baseline', () => {
    const serverNow = new Date(T0).toISOString();
    const expiresAt = new Date(T0 + 5000).toISOString(); // 5s remaining
    const { result } = renderHook(() =>
      useServerTimer(serverNow, expiresAt, vi.fn(), true),
    );

    expect(result.current.timeRemaining).toBe(5);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.timeRemaining).toBe(3);
    expect(result.current.formatTime()).toBe('0:03');
  });

  it('fires onExpire exactly once at zero (auto-submit)', () => {
    const onExpire = vi.fn();
    const serverNow = new Date(T0).toISOString();
    const expiresAt = new Date(T0 + 2000).toISOString(); // 2s
    renderHook(() => useServerTimer(serverNow, expiresAt, onExpire, true));

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);

    // Keep ticking past zero — must not fire again.
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it('does not tick while disabled', () => {
    const serverNow = new Date(T0).toISOString();
    const expiresAt = new Date(T0 + 10000).toISOString();
    const { result } = renderHook(() =>
      useServerTimer(serverNow, expiresAt, vi.fn(), false),
    );
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    // Stays at the baseline; no interval was scheduled.
    expect(result.current.timeRemaining).toBe(10);
  });

  it('flags warning (<5m) and critical (<1m) thresholds', () => {
    const serverNow = new Date(T0).toISOString();
    const expiresAt = new Date(T0 + 30_000).toISOString(); // 30s → critical
    const { result } = renderHook(() =>
      useServerTimer(serverNow, expiresAt, vi.fn(), true),
    );
    expect(result.current.isWarning).toBe(true);
    expect(result.current.isCritical).toBe(true);
  });
});
