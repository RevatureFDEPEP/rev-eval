import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useServerTimer } from "./useServerTimer";

describe("useServerTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("derives the initial remaining from server_now/expires_at", () => {
    const { result } = renderHook(() =>
      useServerTimer("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", () => {}),
    );
    expect(result.current.timeRemaining).toBe(60);
    expect(result.current.formatTime()).toBe("1:00");
  });

  it("anchors to the SERVER delta, not the client clock value (skew absorption)", () => {
    // The client clock is at 2026-01-01; the server window is months later.
    // Remaining must reflect the 120s server delta regardless.
    const { result } = renderHook(() =>
      useServerTimer("2026-06-01T12:00:00Z", "2026-06-01T12:02:00Z", () => {}),
    );
    expect(result.current.timeRemaining).toBe(120);
  });

  it("decrements as wall-clock advances", () => {
    const { result } = renderHook(() =>
      useServerTimer("2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", () => {}),
    );
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.timeRemaining).toBe(55);
  });

  it("fires onExpire exactly once at zero", () => {
    const onExpire = vi.fn();
    renderHook(() =>
      useServerTimer("2026-01-01T00:00:00Z", "2026-01-01T00:00:03Z", onExpire),
    );
    act(() => {
      vi.advanceTimersByTime(6000); // well past expiry
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("does not tick (or expire) when disabled", () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useServerTimer("2026-01-01T00:00:00Z", "2026-01-01T00:00:03Z", onExpire, false),
    );
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onExpire).not.toHaveBeenCalled();
    expect(result.current.timeRemaining).toBe(3); // unchanged baseline
  });

  // W3-F7 item 1 — the gap that let the re-anchor defect slip: every submit
  // toggles `enabled` (active → submitting → active); the countdown must
  // continue from true elapsed time, never reset to the full baseline.
  it("continues from elapsed time after a disable → re-enable cycle (no re-anchor)", () => {
    const { result, rerender } = renderHook(
      ({ enabled }) =>
        useServerTimer(
          "2026-01-01T00:00:00Z",
          "2026-01-01T00:02:00Z",
          () => {},
          enabled,
        ),
      { initialProps: { enabled: true } },
    );
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(result.current.timeRemaining).toBe(90);

    // Submit round-trip: timer disabled for 5s while the request is in flight.
    rerender({ enabled: false });
    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    rerender({ enabled: true });

    // Re-enable re-derives from the ORIGINAL deadline: 120 − 35, not 120.
    expect(result.current.timeRemaining).toBe(85);
  });

  it("keeps the same deadline across multiple toggles", () => {
    const { result, rerender } = renderHook(
      ({ enabled }) =>
        useServerTimer(
          "2026-01-01T00:00:00Z",
          "2026-01-01T00:01:00Z",
          () => {},
          enabled,
        ),
      { initialProps: { enabled: true } },
    );
    for (let i = 0; i < 3; i++) {
      act(() => {
        vi.advanceTimersByTime(10_000);
      });
      rerender({ enabled: false });
      rerender({ enabled: true });
    }
    expect(result.current.timeRemaining).toBe(30); // 60 − 3×10
  });

  it("fires onExpire exactly once even when expiry lands across a re-enable", () => {
    const onExpire = vi.fn();
    const { rerender } = renderHook(
      ({ enabled }) =>
        useServerTimer(
          "2026-01-01T00:00:00Z",
          "2026-01-01T00:00:03Z",
          onExpire,
          enabled,
        ),
      { initialProps: { enabled: true } },
    );
    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    rerender({ enabled: false });
    act(() => {
      vi.advanceTimersByTime(5_000); // deadline passes while disabled
    });
    rerender({ enabled: true }); // immediate tick → expire
    expect(onExpire).toHaveBeenCalledTimes(1);

    rerender({ enabled: false });
    rerender({ enabled: true }); // must not re-fire
    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("flags warning (<5m) and critical (<1m)", () => {
    const { result } = renderHook(() =>
      useServerTimer("2026-01-01T00:00:00Z", "2026-01-01T00:00:30Z", () => {}),
    );
    expect(result.current.isWarning).toBe(true);
    expect(result.current.isCritical).toBe(true);
  });
});
