import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
});
