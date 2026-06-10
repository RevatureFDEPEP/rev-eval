import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import { useAutosave } from "./useAutosave";

describe("useAutosave", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("does not save before the debounce interval elapses", () => {
    const saveFn = vi.fn().mockResolvedValue({});
    const answers = new Map([["q1", [1]]]);
    renderHook(() => useAutosave("s1", answers, true, 30000, saveFn));
    act(() => {
      vi.advanceTimersByTime(29000);
    });
    expect(saveFn).not.toHaveBeenCalled();
  });

  it("saves the full answer map after the 30s debounce", () => {
    const saveFn = vi.fn().mockResolvedValue({});
    const answers = new Map([["q1", [1, 2]]]);
    renderHook(() => useAutosave("s1", answers, true, 30000, saveFn));
    act(() => {
      vi.advanceTimersByTime(30000);
    });
    expect(saveFn).toHaveBeenCalledWith("s1", { q1: [1, 2] });
  });

  it("does not save while disabled (exam locked/submitted)", () => {
    const saveFn = vi.fn().mockResolvedValue({});
    const answers = new Map([["q1", [1]]]);
    renderHook(() => useAutosave("s1", answers, false, 30000, saveFn));
    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(saveFn).not.toHaveBeenCalled();
  });

  it("does not save an empty answer map", () => {
    const saveFn = vi.fn().mockResolvedValue({});
    renderHook(() => useAutosave("s1", new Map(), true, 30000, saveFn));
    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(saveFn).not.toHaveBeenCalled();
  });

  // W3-F7 item 6 — max-wait cap: a candidate editing more often than the
  // interval must still persist a draft every interval (pure trailing
  // debounce would push the save out forever).
  it("fires at the max-wait cap despite continuous edits", () => {
    const saveFn = vi.fn().mockResolvedValue({});
    let answers = new Map([["q1", [0]]]);
    const { rerender } = renderHook(
      ({ a }) => useAutosave("s1", a, true, 30000, saveFn),
      { initialProps: { a: answers } },
    );

    // Edit every 5s — the debounce alone would never reach 30s of quiet.
    for (let t = 5; t <= 25; t += 5) {
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      expect(saveFn).not.toHaveBeenCalled();
      answers = new Map([["q1", [t]]]);
      rerender({ a: answers });
    }

    // 30s after the FIRST unsaved change the capped timer fires.
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);
    expect(saveFn).toHaveBeenCalledWith("s1", { q1: [25] }); // latest state
  });

  // W3-F7 item 6 — a semantic 409/410 means the session is terminal:
  // surface and halt, never keep PATCHing a finished exam.
  it("halts all further autosaves after a semantic 409", async () => {
    const saveFn = vi
      .fn()
      .mockRejectedValue(new ApiError(409, "Conflict", "Session is SUBMITTED"));
    let answers = new Map([["q1", [1]]]);
    const { rerender, result } = renderHook(
      ({ a }) => useAutosave("s1", a, true, 30000, saveFn),
      { initialProps: { a: answers } },
    );

    await act(async () => {
      vi.advanceTimersByTime(30000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);
    expect(result.current).toBe("error");

    // Further changes must not PATCH a terminal session.
    answers = new Map([["q1", [2]]]);
    rerender({ a: answers });
    await act(async () => {
      vi.advanceTimersByTime(60000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);
  });

  it("retries on the next change after a non-semantic failure", async () => {
    const saveFn = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", ""))
      .mockResolvedValueOnce({});
    let answers = new Map([["q1", [1]]]);
    const { rerender } = renderHook(
      ({ a }) => useAutosave("s1", a, true, 30000, saveFn),
      { initialProps: { a: answers } },
    );

    await act(async () => {
      vi.advanceTimersByTime(30000);
    });
    expect(saveFn).toHaveBeenCalledTimes(1);

    answers = new Map([["q1", [1, 2]]]);
    rerender({ a: answers });
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });
    expect(saveFn).toHaveBeenCalledTimes(2);
  });
});
