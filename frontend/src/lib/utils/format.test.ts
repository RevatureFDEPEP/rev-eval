import { describe, expect, it } from "vitest"
import { formatDuration, formatScore } from "./format"

describe("formatDuration", () => {
  it("returns 0s for zero, null, and negative input", () => {
    expect(formatDuration(0)).toBe("0s")
    expect(formatDuration(null)).toBe("0s")
    expect(formatDuration(-5)).toBe("0s")
  })

  it("formats seconds only", () => {
    expect(formatDuration(45)).toBe("45s")
  })

  it("formats minutes and seconds", () => {
    expect(formatDuration(90)).toBe("1m 30s")
    expect(formatDuration(120)).toBe("2m")
  })

  it("formats hours and minutes, dropping seconds", () => {
    expect(formatDuration(3661)).toBe("1h 1m")
    expect(formatDuration(3600)).toBe("1h")
  })
})

describe("formatScore", () => {
  it("rounds to a whole percentage", () => {
    expect(formatScore(87.4)).toBe("87%")
    expect(formatScore(87.6)).toBe("88%")
  })

  it("returns an em dash for missing values", () => {
    expect(formatScore(null)).toBe("—")
    expect(formatScore(undefined)).toBe("—")
  })
})
