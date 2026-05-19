/**
 * Session helpers.
 *
 * The frontend stores the user-service-issued JWT in an httpOnly cookie
 * named AUTH_COOKIE. These helpers decode (without crypto verification —
 * the backend is the source of truth) the token into a session shape.
 */
import 'server-only';
import { cookies } from 'next/headers';
import { decodeJwt } from 'jose';

export const AUTH_COOKIE = 'auth_token';

export interface Session {
  userId: number;
  email: string;
  role: string;
  token: string;
  exp?: number;
}

export interface SessionUser {
  id: number;
  email: string;
  role: string;
}

function decodeToken(token: string): Session | null {
  try {
    const claims = decodeJwt(token);
    if (!claims.sub) return null;
    return {
      userId: Number(claims.sub),
      email: typeof claims.email === 'string' ? claims.email : '',
      role: typeof claims.role === 'string' ? claims.role : '',
      token,
      exp: typeof claims.exp === 'number' ? claims.exp : undefined,
    };
  } catch {
    return null;
  }
}

/** Returns the current session, or null if not signed in or token unparseable/expired. */
export async function getSession(): Promise<Session | null> {
  const jar = await cookies();
  const cookie = jar.get(AUTH_COOKIE);
  if (!cookie?.value) return null;
  const session = decodeToken(cookie.value);
  if (!session) return null;
  if (session.exp && session.exp * 1000 < Date.now()) return null;
  return session;
}

/** Decode the cookie value the middleware (Edge) already extracted. */
export function decodeSessionToken(token: string): Session | null {
  return decodeToken(token);
}

/** Coerce a backend user role to the application role buckets we route on. */
export function normalizeRole(role: string): 'trainer' | 'participant' | 'admin' {
  const r = (role || '').toUpperCase();
  if (r === 'TRAINER') return 'trainer';
  if (r === 'ADMIN') return 'admin';
  return 'participant';
}
