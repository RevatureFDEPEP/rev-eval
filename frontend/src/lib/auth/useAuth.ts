'use client';

import { useEffect, useState } from 'react';
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

/**
 * Client hook that returns the authenticated user.
 * Authkit-compatible surface: `{ user, loading }` and `ensureSignedIn` option.
 */
export function useAuth(options: UseAuthOptions = {}): UseAuthResult {
  const router = useRouter();
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
          if (options.ensureSignedIn) router.replace('/');
          return;
        }
        const data = await res.json();
        setUser(data);
      } catch {
        if (!cancelled) {
          setUser(null);
          if (options.ensureSignedIn) router.replace('/');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [options.ensureSignedIn, router]);

  return { user, loading };
}
