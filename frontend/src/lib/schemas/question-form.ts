import * as z from 'zod'

const baseSchema = {
  question_text: z.string().min(10, 'Question must be at least 10 characters'),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional(),
  skills: z.array(z.string()).min(1, 'Select at least one skill').max(20, 'Maximum 20 skills allowed'),
  tags: z.string().optional().transform((val) => (val ? val.split(',').map((t) => t.trim()) : [])),
  answer_explanation: z.string().optional(),
}

export const mcqSchema = z
  .object({
    ...baseSchema,
    options: z.array(
      z.object({
        text: z.string().min(1, 'Option text is required'),
        is_correct: z.boolean(),
      })
    ),
  })
  .refine(
    (data) => {
      if (data.options.length < 2 || data.options.length > 5) return false
      return data.options.some((opt) => opt.is_correct)
    },
    {
      message: 'MCQ questions require 2-5 options with at least one marked correct',
      path: ['options'],
    }
  )

export const trueFalseSchema = z.object({
  ...baseSchema,
  true_false_answer: z.boolean(),
})

export const textSchema = z.object({
  ...baseSchema,
  sample_answer: z.string().min(10, 'Sample answer must be at least 10 characters'),
})

export type McqFormValues = z.infer<typeof mcqSchema>
export type TrueFalseFormValues = z.infer<typeof trueFalseSchema>
export type TextFormValues = z.infer<typeof textSchema>
export type QuestionFormValues = McqFormValues | TrueFalseFormValues | TextFormValues
