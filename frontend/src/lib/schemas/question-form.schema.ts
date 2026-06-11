import * as z from 'zod'

// Diagram/screenshot upload constraints (spec: .png/.jpg only, ≤ 5 MB).
// Mirrors the server-side policy enforced by the pre-signed POST.
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024
export const ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg'] as const

export const imageFileSchema = z
  .instanceof(File)
  .refine(
    (file) => (ALLOWED_IMAGE_TYPES as readonly string[]).includes(file.type),
    'Only .png or .jpg images are allowed'
  )
  .refine((file) => file.size <= MAX_IMAGE_BYTES, 'Image must be 5MB or smaller')

const baseFields = {
  question_text: z.string().min(10, 'Question must be at least 10 characters'),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional(),
  skills: z
    .array(z.string())
    .min(1, 'Select at least one skill')
    .max(20, 'Maximum 20 skills allowed'),
  tags: z
    .string()
    .optional()
    .transform((val) => (val ? val.split(',').map((t) => t.trim()) : [])),
  answer_explanation: z.string().optional(),
}

export const mcqSchema = z
  .object({
    ...baseFields,
    options: z.array(
      z.object({
        text: z.string().min(1, 'Option text is required'),
        is_correct: z.boolean(),
      })
    ),
  })
  .refine(
    (data) =>
      data.options.length >= 2 &&
      data.options.length <= 5 &&
      data.options.some((opt) => opt.is_correct),
    { message: 'MCQ requires 2–5 options with at least one correct answer' }
  )

export const trueFalseSchema = z.object({
  ...baseFields,
  true_false_answer: z.boolean(),
})

export const textSchema = z.object({
  ...baseFields,
  sample_answer: z.string().min(10, 'Sample answer must be at least 10 characters'),
})

export type McqFormValues = z.infer<typeof mcqSchema>
export type TrueFalseFormValues = z.infer<typeof trueFalseSchema>
export type TextFormValues = z.infer<typeof textSchema>
export type QuestionFormValues = McqFormValues | TrueFalseFormValues | TextFormValues
