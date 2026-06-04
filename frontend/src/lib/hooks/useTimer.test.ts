import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, jest } from "@jest/globals";

import { useTimer } from "./useTimer";

const mockToastWarning = jest.fn();

jest.mock("sonner", () => ({
  toast: {
    warning: mockToastWarning,
  },
}));

describe("useTimer", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-06-04T12:00:00Z"));
    localStorage.clear();
    mockToastWarning.mockReset();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("returns formatted time and warning state from the initial duration", () => {
    const onTimeExpired = jest.fn();

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 125,
        testId: "format",
        onTimeExpired,
        autoStart: false,
      })
    );

    expect(result.current.timeRemaining).toBe(125);
    expect(result.current.formatTime()).toBe("02:05");
    expect(result.current.isWarning).toBe(true);
    expect(result.current.isCritical).toBe(false);
    expect(result.current.isExpired).toBe(false);
  });

  it("counts down while running and persists the remaining time", () => {
    const onTimeExpired = jest.fn();

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 5,
        testId: "countdown",
        onTimeExpired,
      })
    );

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.timeRemaining).toBe(4);
    expect(JSON.parse(localStorage.getItem("quiz-timer-countdown") ?? "{}")).toMatchObject({
      timeRemaining: 4,
    });
  });

  it("pauses, resumes, and resets the timer", () => {
    const onTimeExpired = jest.fn();

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 10,
        testId: "controls",
        onTimeExpired,
      })
    );

    act(() => {
      result.current.pause();
    });

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.timeRemaining).toBe(10);

    act(() => {
      result.current.resume();
    });

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.timeRemaining).toBe(9);

    act(() => {
      result.current.reset(30);
    });

    expect(result.current.timeRemaining).toBe(30);
    expect(result.current.isExpired).toBe(false);
  });

  it("fires the expiration callback once and clears storage", () => {
    const onTimeExpired = jest.fn();

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 1,
        testId: "expire",
        onTimeExpired,
      })
    );

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(result.current.timeRemaining).toBe(0);
    expect(result.current.isExpired).toBe(true);
    expect(localStorage.getItem("quiz-timer-expire")).toBeNull();

    act(() => {
      jest.advanceTimersByTime(100);
    });

    expect(onTimeExpired).toHaveBeenCalledTimes(1);
  });

  it("hydrates remaining time from localStorage", () => {
    localStorage.setItem(
      "quiz-timer-stored",
      JSON.stringify({
        timeRemaining: 20,
        timestamp: Date.now() - 5000,
      })
    );

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 60,
        testId: "stored",
        onTimeExpired: jest.fn(),
        autoStart: false,
      })
    );

    expect(result.current.timeRemaining).toBe(15);
    expect(result.current.formatTime()).toBe("00:15");
  });
});
