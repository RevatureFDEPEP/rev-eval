import { describe, it, expect } from 'vitest';
import { testFormSchema, loginSchema } from './schemas';

describe('testFormSchema', () => {
  it('rejects a name shorter than 3 characters', () => {
    const result = testFormSchema.safeParse({
      name: 'AB',
      role: 'Java Developer',
      duration_minutes: 45,
      number_of_questions: 20,
      active: true,
      skill_ids: [1],
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const nameError = result.error.issues.find((i) => i.path[0] === 'name');
      expect(nameError).toBeDefined();
    }
  });

  it('accepts a fully valid test form payload', () => {
    const result = testFormSchema.safeParse({
      name: 'Java Fundamentals Quiz',
      role: 'Java Developer',
      duration_minutes: 45,
      number_of_questions: 20,
      active: true,
      skill_ids: [1, 2],
    });
    expect(result.success).toBe(true);
  });
});

describe('loginSchema', () => {
  it('rejects a malformed email address', () => {
    const result = loginSchema.safeParse({ email: 'not-an-email', password: 'secret' });
    expect(result.success).toBe(false);
  });
});
