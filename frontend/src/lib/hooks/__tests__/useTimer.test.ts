import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTimer } from '../useTimer';

describe('useTimer — initial state', () => {
  it('initializes with correct timeRemaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 120, testId: 't1', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.timeRemaining).toBe(120);
    expect(result.current.isExpired).toBe(false);
  });

  it('formatTime returns MM:SS', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 125, testId: 't2', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.formatTime()).toBe('02:05');
  });

  it('formatTime pads single-digit seconds', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 61, testId: 't3', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.formatTime()).toBe('01:01');
  });

  it('isWarning true when ≤ 300 s remaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 300, testId: 't4', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.isWarning).toBe(true);
  });

  it('isWarning false when > 300 s remaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 301, testId: 't5', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.isWarning).toBe(false);
  });

  it('isCritical true when ≤ 60 s remaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 60, testId: 't6', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.isCritical).toBe(true);
  });

  it('isCritical false when > 60 s remaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 61, testId: 't7', onTimeExpired: vi.fn(), autoStart: false })
    );
    expect(result.current.isCritical).toBe(false);
  });
});

describe('useTimer — server-anchored mode (expiresAtMs option)', () => {
  it('initializes timeRemaining from expiresAtMs', () => {
    const now = Date.now();
    const expiresAtMs = now + 300_000; // 5 minutes

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 0,
        expiresAtMs,
        testId: 'sa-1',
        onTimeExpired: vi.fn(),
        autoStart: false,
      })
    );

    // Allow ±1s for computation time
    expect(result.current.timeRemaining).toBeGreaterThanOrEqual(299);
    expect(result.current.timeRemaining).toBeLessThanOrEqual(300);
  });
});

describe('useTimer — reset', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('reset with plain duration updates timeRemaining', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 100, testId: 'r1', onTimeExpired: vi.fn(), autoStart: false })
    );

    act(() => {
      result.current.reset(200);
    });

    expect(result.current.timeRemaining).toBe(200);
    expect(result.current.isExpired).toBe(false);
  });

  it('reset with expiresAtMs switches to server-anchored mode', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 0, testId: 'r2', onTimeExpired: vi.fn(), autoStart: false })
    );

    const expiresAtMs = Date.now() + 600_000; // 10 minutes
    act(() => {
      result.current.reset(0, expiresAtMs);
    });

    expect(result.current.timeRemaining).toBeGreaterThanOrEqual(599);
    expect(result.current.timeRemaining).toBeLessThanOrEqual(600);
  });
});

describe('useTimer — countdown and expiry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('decrements timeRemaining on each tick', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 5, testId: 'c1', onTimeExpired: vi.fn(), autoStart: true })
    );

    expect(result.current.timeRemaining).toBe(5);

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(result.current.timeRemaining).toBe(4);
  });

  it('calls onTimeExpired once when timer reaches 0', () => {
    const onExpired = vi.fn();

    renderHook(() =>
      useTimer({ durationSeconds: 2, testId: 'c2', onTimeExpired: onExpired, autoStart: true })
    );

    // Advance one tick at a time so React re-renders between ticks
    // (avoids stale closure: if both ticks fire in one act, the second tick
    //  still sees timeRemaining=2 from the first closure)
    act(() => {
      vi.advanceTimersByTime(1000); // tick 1: timeRemaining → 1
    });
    act(() => {
      vi.advanceTimersByTime(1000); // tick 2: timeRemaining → 0, schedules expiry callback
    });
    // Flush the internal setTimeout(onTimeExpired, 100)
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(onExpired).toHaveBeenCalledTimes(1);
  });

  it('does not call onTimeExpired twice (debounced via ref)', () => {
    const onExpired = vi.fn();

    renderHook(() =>
      useTimer({ durationSeconds: 1, testId: 'c3', onTimeExpired: onExpired, autoStart: true })
    );

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    act(() => {
      vi.advanceTimersByTime(500);
    });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(onExpired).toHaveBeenCalledTimes(1);
  });

  it('pause stops countdown', () => {
    const { result } = renderHook(() =>
      useTimer({ durationSeconds: 5, testId: 'c4', onTimeExpired: vi.fn(), autoStart: true })
    );

    act(() => {
      result.current.pause();
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Should still be 5 (paused before any tick)
    expect(result.current.timeRemaining).toBe(5);
  });
});
