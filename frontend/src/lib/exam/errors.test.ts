import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/client";
import { ExamError, classifyError, fetchWithRetry } from "./errors";

const noSleep = () => Promise.resolve();

describe("classifyError", () => {
  it("treats a network failure (no status) as transient", () => {
    expect(classifyError(undefined)).toBe("transient");
  });

  it("treats 502/503/504 as transient", () => {
    for (const s of [502, 503, 504]) expect(classifyError(s)).toBe("transient");
  });

  it("treats 409/410/422 as semantic", () => {
    for (const s of [409, 410, 422]) expect(classifyError(s)).toBe("semantic");
  });

  it("defaults other statuses to semantic (halt, don't storm)", () => {
    for (const s of [400, 401, 403, 404, 500]) expect(classifyError(s)).toBe("semantic");
  });
});

describe("fetchWithRetry", () => {
  it("returns immediately on success", async () => {
    const fn = vi.fn().mockResolvedValue("ok");
    await expect(fetchWithRetry(fn, { sleep: noSleep })).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("retries a transient failure then succeeds", async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, "Service Unavailable", "x"))
      .mockResolvedValue("ok");
    await expect(fetchWithRetry(fn, { sleep: noSleep })).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does NOT retry a semantic 422 — throws an ExamError immediately", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(422, "Unprocessable", "x"));
    await expect(fetchWithRetry(fn, { sleep: noSleep })).rejects.toBeInstanceOf(ExamError);
    expect(fn).toHaveBeenCalledTimes(1); // no retry storm
  });

  it("gives up after maxRetries transient attempts", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(502, "Bad Gateway", "x"));
    await expect(
      fetchWithRetry(fn, { sleep: noSleep, maxRetries: 2 }),
    ).rejects.toBeInstanceOf(ExamError);
    expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
  });

  it("classifies the thrown ExamError kind from the status", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError(409, "Conflict", "x"));
    await fetchWithRetry(fn, { sleep: noSleep }).catch((err) => {
      expect(err).toBeInstanceOf(ExamError);
      expect((err as ExamError).kind).toBe("semantic");
      expect((err as ExamError).status).toBe(409);
    });
  });
});
