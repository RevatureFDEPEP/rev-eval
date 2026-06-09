import { describe, it, expect } from 'vitest';
import { buildAuthBody, extractErrorMessage } from './auth-helpers';

describe('buildAuthBody', () => {
  it('returns only email and password for login mode', () => {
    const body = buildAuthBody('login', 'user@example.com', 'pass123');
    expect(body).toEqual({ email: 'user@example.com', password: 'pass123' });
    expect(body).not.toHaveProperty('role');
  });

  it('includes role and omits blank full_name for register mode', () => {
    const body = buildAuthBody('register', 'user@example.com', 'pass1234', '', 'TRAINER');
    expect(body).toMatchObject({ email: 'user@example.com', role: 'TRAINER' });
    expect((body as { full_name?: string }).full_name).toBeUndefined();
  });
});

describe('extractErrorMessage', () => {
  it('prefers detail over error and falls back to a mode-specific string', () => {
    expect(extractErrorMessage({ detail: 'Bad credentials' }, 'login')).toBe('Bad credentials');
    expect(extractErrorMessage({ error: 'Duplicate email' }, 'register')).toBe('Duplicate email');
    expect(extractErrorMessage({}, 'login')).toBe('Login failed');
    expect(extractErrorMessage({}, 'register')).toBe('Registration failed');
  });
});
