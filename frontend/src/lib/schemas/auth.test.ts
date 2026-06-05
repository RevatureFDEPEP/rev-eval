import { describe, expect, it, test } from "vitest"
import { loginSchema, registerSchema } from "./auth"

describe("loginSchema", () => {
  it("accepts a valid email and password", () => {
    const result = loginSchema.safeParse({ email: "user@example.com", password: "secret" })
    expect(result.success).toBe(true)
  })

  test.each([
    ["not-an-email", "password"],
    ["missing-at.com", "password"],
    ["@nodomain.com", "password"],
  ])("rejects invalid email: %s", (email, password) => {
    const result = loginSchema.safeParse({ email, password })
    expect(result.success).toBe(false)
  })

  it("rejects empty password", () => {
    const result = loginSchema.safeParse({ email: "user@example.com", password: "" })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe("Password is required")
    }
  })

  it("rejects missing fields", () => {
    expect(loginSchema.safeParse({}).success).toBe(false)
  })
})

describe("registerSchema", () => {
  it("accepts a valid full registration payload", () => {
    const result = registerSchema.safeParse({
      email: "new@example.com",
      password: "securepass",
      full_name: "New User",
      role: "TRAINER",
    })
    expect(result.success).toBe(true)
  })

  it("defaults role to PARTICIPANT when omitted", () => {
    const result = registerSchema.safeParse({ email: "a@b.com", password: "longenough" })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.role).toBe("PARTICIPANT")
    }
  })

  test.each(["short", "1234567", "abcdefg"])(
    "rejects password shorter than 8 characters: %s",
    (password) => {
      const result = registerSchema.safeParse({ email: "a@b.com", password })
      expect(result.success).toBe(false)
    }
  )

  it("rejects password longer than 128 characters", () => {
    const result = registerSchema.safeParse({
      email: "a@b.com",
      password: "a".repeat(129),
    })
    expect(result.success).toBe(false)
  })

  it("rejects invalid role value", () => {
    const result = registerSchema.safeParse({
      email: "a@b.com",
      password: "validpass",
      role: "ADMIN",
    })
    expect(result.success).toBe(false)
  })

  it("makes full_name optional", () => {
    const result = registerSchema.safeParse({ email: "a@b.com", password: "validpass" })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.full_name).toBeUndefined()
    }
  })
})
