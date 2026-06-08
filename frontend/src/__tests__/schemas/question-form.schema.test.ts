import { describe, expect, it } from 'vitest'
import { mcqSchema, textSchema, trueFalseSchema } from '@/lib/schemas/question-form.schema'

const baseValid = {
  question_text: 'What is the capital of France?',
  skills: ['Geography'],
}

describe('mcqSchema', () => {
  const validMcq = {
    ...baseValid,
    options: [
      { text: 'Paris', is_correct: true },
      { text: 'London', is_correct: false },
    ],
  }

  it('accepts valid MCQ with one correct answer', () => {
    expect(mcqSchema.safeParse(validMcq).success).toBe(true)
  })

  it('rejects when no option is correct', () => {
    expect(
      mcqSchema.safeParse({
        ...baseValid,
        options: [
          { text: 'Paris', is_correct: false },
          { text: 'London', is_correct: false },
        ],
      }).success
    ).toBe(false)
  })

  it('rejects fewer than 2 options', () => {
    expect(
      mcqSchema.safeParse({ ...baseValid, options: [{ text: 'Paris', is_correct: true }] }).success
    ).toBe(false)
  })

  it('rejects more than 5 options', () => {
    const options = Array.from({ length: 6 }, (_, i) => ({ text: `Option ${i}`, is_correct: i === 0 }))
    expect(mcqSchema.safeParse({ ...baseValid, options }).success).toBe(false)
  })

  it('rejects question_text shorter than 10 chars', () => {
    expect(mcqSchema.safeParse({ ...validMcq, question_text: 'Short?' }).success).toBe(false)
  })

  it('rejects empty skills array', () => {
    expect(mcqSchema.safeParse({ ...validMcq, skills: [] }).success).toBe(false)
  })
})

describe('trueFalseSchema', () => {
  it('accepts correct_answer=true', () => {
    expect(trueFalseSchema.safeParse({ ...baseValid, correct_answer: true }).success).toBe(true)
  })

  it('accepts correct_answer=false', () => {
    expect(trueFalseSchema.safeParse({ ...baseValid, correct_answer: false }).success).toBe(true)
  })

  it('rejects question_text shorter than 10 chars', () => {
    expect(
      trueFalseSchema.safeParse({ question_text: 'Hi?', skills: ['x'], correct_answer: true }).success
    ).toBe(false)
  })
})

describe('textSchema', () => {
  it('accepts valid text question', () => {
    expect(textSchema.safeParse(baseValid).success).toBe(true)
  })

  it('rejects empty skills', () => {
    expect(textSchema.safeParse({ ...baseValid, skills: [] }).success).toBe(false)
  })

  it('transforms comma-separated tags to array', () => {
    const result = textSchema.safeParse({ ...baseValid, tags: 'java, oop, patterns' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags).toEqual(['java', 'oop', 'patterns'])
    }
  })

  it('returns empty array when tags omitted', () => {
    const result = textSchema.safeParse(baseValid)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags).toEqual([])
    }
  })
})
