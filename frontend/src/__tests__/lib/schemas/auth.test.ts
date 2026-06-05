import { loginSchema, registerSchema } from '@/lib/schemas/auth'

describe('loginSchema', () => {
  it('accepts valid email and password', () => {
    expect(loginSchema.safeParse({ email: 'user@example.com', password: 'secret' }).success).toBe(true)
  })

  it('rejects invalid email format', () => {
    const result = loginSchema.safeParse({ email: 'not-an-email', password: 'secret' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('email'))).toBe(true)
    }
  })

  it('rejects empty password', () => {
    const result = loginSchema.safeParse({ email: 'user@example.com', password: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('password'))).toBe(true)
    }
  })

  it('rejects missing email field', () => {
    const result = loginSchema.safeParse({ password: 'secret' })
    expect(result.success).toBe(false)
  })

  it('rejects missing password field', () => {
    const result = loginSchema.safeParse({ email: 'user@example.com' })
    expect(result.success).toBe(false)
  })
})

describe('registerSchema', () => {
  const VALID = {
    email: 'newuser@example.com',
    password: 'password123',
    role: 'PARTICIPANT' as const,
  }

  it('accepts valid registration data for PARTICIPANT', () => {
    expect(registerSchema.safeParse(VALID).success).toBe(true)
  })

  it('accepts TRAINER role', () => {
    expect(registerSchema.safeParse({ ...VALID, role: 'TRAINER' }).success).toBe(true)
  })

  it('accepts optional full_name', () => {
    expect(registerSchema.safeParse({ ...VALID, full_name: 'Jane Doe' }).success).toBe(true)
  })

  it('rejects password shorter than 8 characters', () => {
    const result = registerSchema.safeParse({ ...VALID, password: 'short' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('password'))).toBe(true)
    }
  })

  it('rejects invalid role value', () => {
    const result = registerSchema.safeParse({ ...VALID, role: 'ADMIN' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('role'))).toBe(true)
    }
  })

  it('rejects invalid email format', () => {
    const result = registerSchema.safeParse({ ...VALID, email: 'bad-email' })
    expect(result.success).toBe(false)
  })
})
