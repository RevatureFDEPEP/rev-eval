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
  it('accepts true_false_answer=true', () => {
    expect(trueFalseSchema.safeParse({ ...baseValid, true_false_answer: true }).success).toBe(true)
  })

  it('accepts true_false_answer=false', () => {
    expect(trueFalseSchema.safeParse({ ...baseValid, true_false_answer: false }).success).toBe(true)
  })

  it('rejects question_text shorter than 10 chars', () => {
    expect(
      trueFalseSchema.safeParse({ question_text: 'Hi?', skills: ['x'], true_false_answer: true }).success
    ).toBe(false)
  })
})

const validText = {
  ...baseValid,
  sample_answer: 'This is a valid sample answer',
}

describe('textSchema', () => {
  it('accepts valid text question', () => {
    expect(textSchema.safeParse(validText).success).toBe(true)
  })

  it('rejects empty skills', () => {
    expect(textSchema.safeParse({ ...validText, skills: [] }).success).toBe(false)
  })

  it('rejects sample_answer shorter than 10 chars', () => {
    expect(textSchema.safeParse({ ...validText, sample_answer: 'Too short' }).success).toBe(false)
  })

  it('transforms comma-separated tags to array', () => {
    const result = textSchema.safeParse({ ...validText, tags: 'java, oop, patterns' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags).toEqual(['java', 'oop', 'patterns'])
    }
  })

  it('returns empty array when tags omitted', () => {
    const result = textSchema.safeParse(validText)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags).toEqual([])
    }
  })
})
