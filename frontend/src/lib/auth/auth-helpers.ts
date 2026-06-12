export type AuthMode = 'login' | 'register';

export interface LoginBody {
  email: string;
  password: string;
}

export interface RegisterBody {
  email: string;
  password: string;
  full_name?: string;
  role: 'PARTICIPANT' | 'TRAINER';
}

export function buildAuthBody(
  mode: AuthMode,
  email: string,
  password: string,
  fullName?: string,
  role: 'PARTICIPANT' | 'TRAINER' = 'PARTICIPANT'
): LoginBody | RegisterBody {
  if (mode === 'login') {
    return { email, password };
  }
  return { email, password, full_name: fullName || undefined, role };
}

export function extractErrorMessage(
  data: Record<string, unknown>,
  mode: AuthMode
): string {
  const fallback = mode === 'login' ? 'Login failed' : 'Registration failed';
  return (data.detail as string) ?? (data.error as string) ?? fallback;
}
