import { describe, expect, it } from 'vitest'
import { testFormSchema } from '@/lib/schemas/test-form.schema'

const validInput = {
  name: 'Java Fundamentals',
  role: 'Junior Developer',
  duration_minutes: 45,
  number_of_questions: 20,
  active: true,
  skill_ids: [1, 2],
}

describe('testFormSchema', () => {
  it('accepts valid input', () => {
    expect(testFormSchema.safeParse(validInput).success).toBe(true)
  })

  it.each([
    ['ab', 'below 3 chars'],
    ['', 'empty'],
  ])('rejects name "%s" (%s)', (name) => {
    expect(testFormSchema.safeParse({ ...validInput, name }).success).toBe(false)
  })

  it.each([
    [4, 'below min'],
    [241, 'above max'],
  ])('rejects duration_minutes=%i (%s)', (duration_minutes) => {
    expect(testFormSchema.safeParse({ ...validInput, duration_minutes }).success).toBe(false)
  })

  it.each([
    [9, 'below min'],
    [51, 'above max'],
  ])('rejects number_of_questions=%i (%s)', (number_of_questions) => {
    expect(testFormSchema.safeParse({ ...validInput, number_of_questions }).success).toBe(false)
  })

  it('rejects empty skill_ids', () => {
    expect(testFormSchema.safeParse({ ...validInput, skill_ids: [] }).success).toBe(false)
  })

  it('rejects empty role', () => {
    expect(testFormSchema.safeParse({ ...validInput, role: '' }).success).toBe(false)
  })

  it('accepts boundary: min duration and min questions', () => {
    expect(
      testFormSchema.safeParse({ ...validInput, duration_minutes: 5, number_of_questions: 10 }).success
    ).toBe(true)
  })

  it('accepts boundary: max duration and max questions', () => {
    expect(
      testFormSchema.safeParse({ ...validInput, duration_minutes: 240, number_of_questions: 50 }).success
    ).toBe(true)
  })
})
