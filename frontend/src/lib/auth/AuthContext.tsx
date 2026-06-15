'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { AuthIdentity } from '@/lib/api/types';

const AuthContext = createContext<AuthIdentity | null>(null);

/**
 * Exposes the candidate's display identity (userId/email/role) to the client
 * tree. Seeded server-side from already-verified JWT claims — the raw auth
 * cookie is never placed in `window` or the JS bundle; the gateway remains the
 * security boundary (W3-F3 step 5).
 */
export function AuthProvider({
  identity,
  children,
}: {
  identity: AuthIdentity;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={identity}>{children}</AuthContext.Provider>;
}

/** Read the seeded identity. Throws if used outside an <AuthProvider>. */
export function useAuthContext(): AuthIdentity {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuthContext must be used within an <AuthProvider>');
  }
  return ctx;
}
