import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import { toast } from "sonner";

import { useTimer } from "./useTimer";

describe("useTimer", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-06-04T12:00:00Z"));
    localStorage.clear();
    jest.spyOn(toast, "warning").mockImplementation(() => undefined as never);
  });

  afterEach(() => {
    jest.restoreAllMocks();
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

  it("shows 5-minute and 1-minute warnings once when thresholds are crossed", async () => {
    renderHook(() =>
      useTimer({
        durationSeconds: 301,
        testId: "warnings",
        onTimeExpired: jest.fn(),
      })
    );

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(toast.warning).toHaveBeenCalledWith(
        "5 Minutes Remaining",
        expect.objectContaining({
          description: "Please review your answers.",
        })
      );
    });

    await act(async () => {
      jest.advanceTimersByTime(240000);
    });

    await waitFor(() => {
      expect(toast.warning).toHaveBeenCalledWith(
        "1 Minute Remaining!",
        expect.objectContaining({
          description: "Test will auto-submit when time expires.",
        })
      );
      expect(toast.warning).toHaveBeenCalledTimes(2);
    });

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    expect(toast.warning).toHaveBeenCalledTimes(2);
  });

  it("hydrates remaining time from localStorage", async () => {
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

    await waitFor(() => {
      expect(result.current.timeRemaining).toBe(15);
    });
    expect(result.current.formatTime()).toBe("00:15");
  });

  it("expires once when stored time has already elapsed", async () => {
    const onTimeExpired = jest.fn();
    localStorage.setItem(
      "quiz-timer-expired-stored",
      JSON.stringify({
        timeRemaining: 20,
        timestamp: Date.now() - 30000,
      })
    );

    const { result } = renderHook(() =>
      useTimer({
        durationSeconds: 60,
        testId: "expired-stored",
        onTimeExpired,
      })
    );

    await waitFor(() => {
      expect(result.current.timeRemaining).toBe(0);
    });
    expect(result.current.formatTime()).toBe("00:00");
    expect(result.current.isExpired).toBe(true);
    await waitFor(() => {
      expect(localStorage.getItem("quiz-timer-expired-stored")).toBeNull();
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    expect(onTimeExpired).toHaveBeenCalledTimes(1);
  });
});
