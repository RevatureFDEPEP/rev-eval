import { describe, expect, it } from 'vitest'

import { loginSchema, registerSchema } from '@/lib/schemas/auth'

describe('loginSchema', () => {
  it('passes with a valid email and password', () => {
    const result = loginSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
    })
    expect(result.success).toBe(true)
  })

  it('fails on an invalid email format', () => {
    const result = loginSchema.safeParse({
      email: 'not-an-email',
      password: 'password123',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe('Invalid email address')
    }
  })

  it('fails when password is under 8 characters', () => {
    const result = loginSchema.safeParse({
      email: 'user@example.com',
      password: 'short',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe('Password must be at least 8 characters')
    }
  })
})

describe('registerSchema', () => {
  it('defaults role to PARTICIPANT when omitted', () => {
    const result = registerSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.role).toBe('PARTICIPANT')
    }
  })

  it('fails on an invalid role value', () => {
    const result = registerSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
      role: 'ADMIN',
    })
    expect(result.success).toBe(false)
  })

  it('accepts TRAINER as a role', () => {
    const result = registerSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
      role: 'TRAINER',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.role).toBe('TRAINER')
    }
  })

  it('treats full_name as optional', () => {
    const result = registerSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.full_name).toBeUndefined()
    }
  })

  it('accepts full_name when provided', () => {
    const result = registerSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
      full_name: 'Test User',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.full_name).toBe('Test User')
    }
  })
})
