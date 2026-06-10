import { mcqSchema, trueFalseSchema, textSchema } from '@/lib/schemas/question-form'

const BASE = {
  question_text: 'What is the purpose of Java interfaces?',
  difficulty: 'medium' as const,
  skills: ['Java'],
  tags: '',
}

describe('mcqSchema', () => {
  const VALID_MCQ = {
    ...BASE,
    options: [
      { text: 'Define contracts', is_correct: true },
      { text: 'Store data', is_correct: false },
      { text: 'Replace classes', is_correct: false },
    ],
  }

  it('accepts valid MCQ data', () => {
    expect(mcqSchema.safeParse(VALID_MCQ).success).toBe(true)
  })

  it('rejects question_text shorter than 10 characters', () => {
    const result = mcqSchema.safeParse({ ...VALID_MCQ, question_text: 'Short?' })
    expect(result.success).toBe(false)
  })

  it('rejects MCQ with fewer than 2 options', () => {
    const result = mcqSchema.safeParse({
      ...VALID_MCQ,
      options: [{ text: 'Only option', is_correct: true }],
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('options'))).toBe(true)
    }
  })

  it('rejects MCQ with more than 5 options', () => {
    const result = mcqSchema.safeParse({
      ...VALID_MCQ,
      options: Array.from({ length: 6 }, (_, i) => ({ text: `Option ${i}`, is_correct: i === 0 })),
    })
    expect(result.success).toBe(false)
  })

  it('rejects MCQ with no correct option', () => {
    const result = mcqSchema.safeParse({
      ...VALID_MCQ,
      options: [
        { text: 'Option A', is_correct: false },
        { text: 'Option B', is_correct: false },
      ],
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty option text', () => {
    const result = mcqSchema.safeParse({
      ...VALID_MCQ,
      options: [
        { text: '', is_correct: true },
        { text: 'Option B', is_correct: false },
      ],
    })
    expect(result.success).toBe(false)
  })

  it('rejects empty skills array', () => {
    const result = mcqSchema.safeParse({ ...VALID_MCQ, skills: [] })
    expect(result.success).toBe(false)
  })

  it('transforms tags csv string into array', () => {
    const result = mcqSchema.safeParse({ ...VALID_MCQ, tags: 'java, oop, interfaces' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.tags).toEqual(['java', 'oop', 'interfaces'])
    }
  })
})

describe('trueFalseSchema', () => {
  const VALID_TF = {
    ...BASE,
    true_false_answer: true,
  }

  it('accepts valid true/false data', () => {
    expect(trueFalseSchema.safeParse(VALID_TF).success).toBe(true)
  })

  it('accepts false as the correct answer', () => {
    expect(trueFalseSchema.safeParse({ ...VALID_TF, true_false_answer: false }).success).toBe(true)
  })

  it('rejects when true_false_answer is missing', () => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { true_false_answer: _, ...rest } = VALID_TF
    const result = trueFalseSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects question_text shorter than 10 characters', () => {
    const result = trueFalseSchema.safeParse({ ...VALID_TF, question_text: 'Too short' })
    expect(result.success).toBe(false)
  })
})

describe('textSchema', () => {
  const VALID_TEXT = {
    ...BASE,
    sample_answer: 'Java interfaces define a contract that classes must implement.',
  }

  it('accepts valid text question data', () => {
    expect(textSchema.safeParse(VALID_TEXT).success).toBe(true)
  })

  it('rejects sample_answer shorter than 10 characters', () => {
    const result = textSchema.safeParse({ ...VALID_TEXT, sample_answer: 'Short' })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path.includes('sample_answer'))).toBe(true)
    }
  })

  it('rejects when sample_answer is missing', () => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { sample_answer: _, ...rest } = VALID_TEXT
    const result = textSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })
})
