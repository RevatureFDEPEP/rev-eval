'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from './AuthContext';

export interface AuthUser {
  id: number;
  email: string;
  firstName?: string;
  lastName?: string;
  fullName?: string;
  role: string;
  organizationId?: string;
}

interface UseAuthOptions {
  ensureSignedIn?: boolean;
}

interface UseAuthResult {
  user: AuthUser | null;
  loading: boolean;
}

export function useAuth(options: UseAuthOptions = {}): UseAuthResult {
  const ctx = useAuthContext();
  const router = useRouter();
  const routerRef = useRef(router);
  routerRef.current = router;

  const ensureSignedIn = options.ensureSignedIn;

  // Fallback state used only when no AuthProvider is present
  const [localUser, setLocalUser] = useState<AuthUser | null>(null);
  const [localLoading, setLocalLoading] = useState(true);

  // Redirect when context resolves to unauthenticated
  useEffect(() => {
    if (ctx === null) return;
    if (!ctx.loading && !ctx.user && ensureSignedIn) {
      routerRef.current.replace('/');
    }
  }, [ctx, ensureSignedIn]);

  // Standalone fetch — only runs when there is no AuthProvider
  useEffect(() => {
    if (ctx !== null) return;

    let cancelled = false;

    async function load() {
      try {
        const res = await fetch('/api/auth/me', { cache: 'no-store' });
        if (cancelled) return;
        if (!res.ok) {
          setLocalUser(null);
          if (ensureSignedIn) routerRef.current.replace('/');
          return;
        }
        const data: AuthUser = await res.json();
        setLocalUser((prev) => (prev?.id === data.id && prev?.role === data.role ? prev : data));
      } catch {
        if (!cancelled) {
          setLocalUser(null);
          if (ensureSignedIn) routerRef.current.replace('/');
        }
      } finally {
        if (!cancelled) setLocalLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [ensureSignedIn, ctx]);

  if (ctx !== null) {
    return { user: ctx.user, loading: ctx.loading };
  }
  return { user: localUser, loading: localLoading };
}
