import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

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
}

async function verifySession(token: string | undefined): Promise<DecodedSession | null> {
  if (!token) return null;
  const secret = process.env.JWT_SECRET;
  if (!secret) return null;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret));
    if (!payload.sub) return null;
    const role = typeof payload.role === 'string' ? payload.role.toUpperCase() : '';
    return { userId: String(payload.sub), role };
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const session = await verifySession(token);

  if (!session) {
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
