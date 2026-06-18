'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { AuthIdentity } from '@/lib/api/types';

const AuthContext = createContext<AuthIdentity | null>(null);

export function AuthProvider({
  identity,
  children,
}: {
  identity: AuthIdentity;
  children: ReactNode;
}) {
  return <AuthContext.Provider value={identity}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthIdentity {
  const identity = useContext(AuthContext);
  if (identity === null) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return identity;
}
