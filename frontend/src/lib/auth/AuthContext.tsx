/**
 * AuthContext (W3-F3).
 *
 * Exposes the authenticated user's derived identity (id, email, role, names)
 * to the client tree. The provider is SERVER-SEEDED: the server component
 * fetches the validated identity (GET /v1/api/auth/me) and passes it as the
 * `user` prop, so the raw httpOnly auth cookie never enters `window` or the JS
 * bundle. Reused by W4-F2 (results page) and W4-F4 (trainer route guards).
 */

'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { AuthUser } from './useAuth';

interface AuthContextValue {
  user: AuthUser | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({
  user,
  children,
}: {
  user: AuthUser | null;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={{ user }}>{children}</AuthContext.Provider>;
}

/** Read the server-seeded identity. Throws if used outside an AuthProvider. */
export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return ctx;
}
