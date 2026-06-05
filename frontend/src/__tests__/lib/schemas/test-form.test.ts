import { testFormSchema } from '@/lib/schemas/test-form'

const VALID = {
  name: 'Java Fundamentals Quiz',
  role: 'Java Developer',
  duration_minutes: 45,
  number_of_questions: 20,
  active: true,
  skill_ids: [1, 2],
}

describe('testFormSchema', () => {
  it('accepts valid data', () => {
    expect(testFormSchema.safeParse(VALID).success).toBe(true)
  })

  it('rejects name shorter than 3 characters', () => {
    const result = testFormSchema.safeParse({ ...VALID, name: 'AB' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('name'))).toBe(true)
    }
  })

  it('rejects empty role', () => {
    const result = testFormSchema.safeParse({ ...VALID, role: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('role'))).toBe(true)
    }
  })

  it('rejects duration_minutes below 5', () => {
    const result = testFormSchema.safeParse({ ...VALID, duration_minutes: 4 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('duration_minutes'))).toBe(true)
    }
  })

  it('rejects duration_minutes above 240', () => {
    const result = testFormSchema.safeParse({ ...VALID, duration_minutes: 241 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('duration_minutes'))).toBe(true)
    }
  })

  it('rejects number_of_questions below 10', () => {
    const result = testFormSchema.safeParse({ ...VALID, number_of_questions: 9 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('number_of_questions'))).toBe(true)
    }
  })

  it('rejects number_of_questions above 50', () => {
    const result = testFormSchema.safeParse({ ...VALID, number_of_questions: 51 })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('number_of_questions'))).toBe(true)
    }
  })

  it('rejects empty skill_ids array', () => {
    const result = testFormSchema.safeParse({ ...VALID, skill_ids: [] })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('skill_ids'))).toBe(true)
    }
  })

  it('accepts boundary values: duration 5 and 240', () => {
    expect(testFormSchema.safeParse({ ...VALID, duration_minutes: 5 }).success).toBe(true)
    expect(testFormSchema.safeParse({ ...VALID, duration_minutes: 240 }).success).toBe(true)
  })

  it('accepts boundary values: number_of_questions 10 and 50', () => {
    expect(testFormSchema.safeParse({ ...VALID, number_of_questions: 10 }).success).toBe(true)
    expect(testFormSchema.safeParse({ ...VALID, number_of_questions: 50 }).success).toBe(true)
  })
})
