import * as z from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

export const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Minimum 8 characters'),
  full_name: z.string().optional(),
  role: z.enum(['PARTICIPANT', 'TRAINER']),
});

export const testFormSchema = z.object({
  name: z.string().min(3, 'Test name must be at least 3 characters'),
  role: z.string().min(1, 'Role is required'),
  duration_minutes: z
    .number()
    .min(5, 'Minimum duration is 5 minutes')
    .max(240, 'Maximum duration is 240 minutes'),
  number_of_questions: z
    .number()
    .min(10, 'Minimum 10 questions')
    .max(50, 'Maximum 50 questions'),
  active: z.boolean(),
  skill_ids: z.array(z.number()).min(1, 'Select at least one skill'),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
export type RegisterFormValues = z.infer<typeof registerSchema>;
export type TestFormValues = z.infer<typeof testFormSchema>;
