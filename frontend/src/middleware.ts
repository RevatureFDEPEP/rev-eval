import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { decodeJwt } from 'jose';

const AUTH_COOKIE = 'auth_token';

const PUBLIC_PATHS = new Set<string>([
  '/',
  '/unauthorized',
]);

const PUBLIC_PATH_PREFIXES = ['/api/auth/'];

const roleProtectedRoutes: Record<string, string[]> = {
  '/trainer': ['TRAINER', 'ADMIN'],
  '/participant': ['PARTICIPANT'],
  '/dashboard': ['TRAINER', 'PARTICIPANT', 'ADMIN'],
};

function isPublic(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;
  return PUBLIC_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

interface DecodedSession {
  userId: string;
  role: string;
  expired: boolean;
}

function decodeSession(token: string | undefined): DecodedSession | null {
  if (!token) return null;
  try {
    const claims = decodeJwt(token);
    if (!claims.sub) return null;
    const role = typeof claims.role === 'string' ? claims.role.toUpperCase() : '';
    const expired = typeof claims.exp === 'number' ? claims.exp * 1000 < Date.now() : false;
    return { userId: String(claims.sub), role, expired };
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const session = decodeSession(token);

  if (!session || session.expired) {
    const loginUrl = new URL('/', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Dashboard auto-redirect by role
  if (pathname === '/dashboard') {
    if (session.role === 'TRAINER' || session.role === 'ADMIN') {
      return NextResponse.redirect(new URL('/trainer/dashboard', request.url));
    }
    return NextResponse.redirect(new URL('/participant/dashboard', request.url));
  }

  // Role-protected prefixes
  const protectedEntry = Object.entries(roleProtectedRoutes).find(
    ([prefix]) => pathname.startsWith(prefix),
  );
  if (protectedEntry) {
    const [, allowedRoles] = protectedEntry;
    if (!allowedRoles.includes(session.role)) {
      return NextResponse.redirect(new URL('/unauthorized', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
