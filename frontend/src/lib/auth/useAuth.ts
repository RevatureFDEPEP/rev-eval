'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

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
  const router = useRouter();
  const routerRef = useRef(router);
  routerRef.current = router;

  const ensureSignedIn = options.ensureSignedIn;
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch('/api/auth/me', { cache: 'no-store' });
        if (cancelled) return;
        if (!res.ok) {
          setUser(null);
          if (ensureSignedIn) routerRef.current.replace('/');
          return;
        }
        const data: AuthUser = await res.json();
        setUser((prev) => (prev?.id === data.id && prev?.role === data.role ? prev : data));
      } catch {
        if (!cancelled) {
          setUser(null);
          if (ensureSignedIn) routerRef.current.replace('/');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [ensureSignedIn]);

  return { user, loading };
}
