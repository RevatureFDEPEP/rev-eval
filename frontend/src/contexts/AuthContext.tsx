'use client';

import { createContext, useContext } from 'react';

export interface AuthUser {
  id: number;
  email: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
}

const AuthContext = createContext<AuthContextValue>({ user: null });

export function AuthContextProvider({
  children,
  user,
}: {
  children: React.ReactNode;
  user: AuthUser | null;
}) {
  return <AuthContext.Provider value={{ user }}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  return useContext(AuthContext);
}
