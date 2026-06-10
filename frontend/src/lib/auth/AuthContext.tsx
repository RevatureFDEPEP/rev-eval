/**
 * AuthContext — exposes the authenticated user's display identity to the client
 * component tree.
 *
 * The identity (`user_id` / `email` / `role`) is fetched **server-side** (see
 * `getIdentityServer()` in `@/lib/api/server`) and passed in as `initialUser`,
 * so the raw httpOnly `auth_token` cookie is never serialized into `window` or
 * the JS bundle — only the derived, non-sensitive identity crosses the boundary.
 */
'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { AuthIdentity } from '@/lib/api/types';

const AuthContext = createContext<AuthIdentity | null>(null);

interface AuthProviderProps {
  initialUser: AuthIdentity;
  children: ReactNode;
}

export function AuthProvider({ initialUser, children }: AuthProviderProps) {
  return <AuthContext.Provider value={initialUser}>{children}</AuthContext.Provider>;
}

/** Read the server-seeded identity. Throws if used outside an <AuthProvider>. */
export function useAuthContext(): AuthIdentity {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuthContext must be used within an <AuthProvider>');
  }
  return ctx;
}
