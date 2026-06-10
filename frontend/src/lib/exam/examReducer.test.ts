import { describe, expect, it } from "vitest";
import { examReducer, initialExamState } from "./examReducer";

describe("examReducer", () => {
  it("starts active and unlocked", () => {
    expect(initialExamState.status).toBe("active");
    expect(initialExamState.isLocked).toBe(false);
  });

  it("SUBMIT_START optimistically locks before the server responds", () => {
    const s = examReducer(initialExamState, { type: "SUBMIT_START" });
    expect(s.status).toBe("submitting");
    expect(s.isLocked).toBe(true);
    expect(s.error).toBeNull();
  });

  it("SUBMIT_CONFIRMED finalized → submitted and STAYS locked", () => {
    const mid = examReducer(initialExamState, { type: "SUBMIT_START" });
    const s = examReducer(mid, {
      type: "SUBMIT_CONFIRMED",
      finalized: true,
      submittedAt: "2026-01-01T00:00:00Z",
    });
    expect(s.status).toBe("submitted");
    expect(s.isLocked).toBe(true);
    expect(s.submittedAt).toBe("2026-01-01T00:00:00Z");
  });

  it("SUBMIT_CONFIRMED not finalized → active and unlocked (next question)", () => {
    const mid = examReducer(initialExamState, { type: "SUBMIT_START" });
    const s = examReducer(mid, { type: "SUBMIT_CONFIRMED", finalized: false });
    expect(s.status).toBe("active");
    expect(s.isLocked).toBe(false);
  });

  it("SUBMIT_FAILED → error, stays locked, records the kind + message", () => {
    const mid = examReducer(initialExamState, { type: "SUBMIT_START" });
    const s = examReducer(mid, {
      type: "SUBMIT_FAILED",
      kind: "semantic",
      message: "rejected",
    });
    expect(s.status).toBe("error");
    expect(s.isLocked).toBe(true);
    expect(s.error).toEqual({ kind: "semantic", message: "rejected" });
  });
});
