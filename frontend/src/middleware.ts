import { authkitMiddleware, authkit } from '@workos-inc/authkit-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest, NextFetchEvent } from 'next/server';

const AUTH_MODE = process.env.AUTH_MODE === 'OFF' ? false : true;
const ORG_ID = process.env.WORKOS_DEFAULT_ORG || 'org_L0C4L';

// Define role-protected routes
const roleProtectedRoutes: Record<string, string[]> = {
  '/trainer': ['org-trainer', 'trainer', 'org-admin', 'admin'],
  '/participant': ['org-participant', 'participant', 'member'],
  '/dashboard': ['org-trainer', 'trainer', 'org-admin', 'admin', 'org-participant', 'participant', 'member'],
};

const baseAuthMiddleware = authkitMiddleware({
  middlewareAuth: {
    enabled: AUTH_MODE,
    unauthenticatedPaths: [
      '/',
      '/auth/login',
      '/auth/logout',
      '/api/auth/callback',
      '/api/auth/login',
      '/api/auth/logout',
      '/unauthorized',
    ],
  },
  redirectUri: process.env['NEXT_PUBLIC_WORKOS_REDIRECT_URI'],
});

export async function middleware(request: NextRequest, event: NextFetchEvent) {
  const { pathname } = request.nextUrl;

  const authResponse = await baseAuthMiddleware(request, event);

  if (authResponse && authResponse.headers.has('location')) {
    console.log('location header present:', authResponse.headers.get('location'));
    if (new URL(authResponse.headers.get('location')!, request.url).pathname !== pathname) {
      return authResponse;
    }
  }

  // Handle dashboard routing based on role
  if (pathname === '/dashboard') {
    const { role, organizationId } = AUTH_MODE 
      ? (await authkit(request, { debug: true })).session 
      : { role: 'member', organizationId: ORG_ID };

    console.log('Dashboard routing - User role:', role);
    console.log('Dashboard routing - Organization ID:', organizationId);

    // Check organization membership
    if (organizationId !== ORG_ID) {
      console.log(`Unauthorized access attempt to ${pathname}. Invalid organization ID: ${organizationId}`);
      const unauthorizedRedirectUrl = new URL("/unauthorized", request.url);
      return NextResponse.redirect(unauthorizedRedirectUrl);
    }

    // Redirect based on role
    if (role === 'org-trainer' || role === 'trainer') {
      console.log('Redirecting trainer to trainer dashboard');
      return NextResponse.redirect(new URL('/trainer/dashboard', request.url));
    } else if (role === 'org-admin' || role === 'admin') {
      console.log('Redirecting admin to admin dashboard');
      return NextResponse.redirect(new URL('/dashboard', request.url));
    } else {
      console.log('Redirecting to participant dashboard');
      return NextResponse.redirect(new URL('/participant/dashboard', request.url));
    }
  }

  // Check if route requires role protection
  const requiredRolesForRoute = Object.entries(roleProtectedRoutes).find(
    ([routePrefix]) => pathname.startsWith(routePrefix)
  )?.[1];

  console.log('Required roles for route:', requiredRolesForRoute);

  if (!requiredRolesForRoute) {
    console.log(`No role protection for ${pathname}.`);
    return authResponse || NextResponse.next();
  }

  // Get user session with role information
  const { role, organizationId } = AUTH_MODE 
    ? (await authkit(request, { debug: true })).session 
    : { role: 'member', organizationId: ORG_ID };

  console.log('User role:', role);
  console.log('User organization ID:', organizationId);
  console.log('Default org id:', ORG_ID);

  // Check organization membership
  if (organizationId !== ORG_ID) {
    console.log(`Unauthorized access attempt to ${pathname}. Invalid organization ID: ${organizationId}`);
    const unauthorizedRedirectUrl = new URL("/unauthorized", request.url);
    return NextResponse.redirect(unauthorizedRedirectUrl);
  }

  // Check if user has required role
  const hasRequiredRole = requiredRolesForRoute.some(requiredRole => role === requiredRole);
  console.log(`User role: ${role}, Required roles: [${requiredRolesForRoute.join(', ')}], Has required role: ${hasRequiredRole}`);

  if (!hasRequiredRole) {
    console.log(`Unauthorized access attempt to ${pathname}. User roles: ${role}, Required roles: [${requiredRolesForRoute.join(', ')}]`);
    const unauthorizedRedirectUrl = new URL("/unauthorized", request.url);
    return NextResponse.redirect(unauthorizedRedirectUrl);
  }

  return authResponse || NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
