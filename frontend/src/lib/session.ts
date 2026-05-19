import { authkit } from '@workos-inc/authkit-nextjs';
import { NextRequest } from 'next/server';

/**
 * Gets user session data with role information
 * @param request - NextRequest object
 * @returns Promise with session data including role and organizationId
 */
export async function getSessionWithRole(request: NextRequest) {
  try {
    const sessionData = await authkit(request, { debug: true });
    return sessionData.session;
  } catch (error) {
    console.error('Error getting session with role:', error);
    return null;
  }
}

/**
 * Gets user role from session data
 * @param session - Session object from authkit
 * @returns UserRole based on session role
 */
export function getRoleFromSession(session: any): 'trainer' | 'associate' | 'admin' {
  if (!session || !session.role) {
    return 'associate';
  }

  // Map WorkOS roles to our application roles
  switch (session.role) {
    case 'org-trainer':
    case 'trainer':
      return 'trainer';
    case 'org-admin':
    case 'admin':
      return 'admin';
    case 'org-participant':
    case 'participant':
    case 'member':
      return 'associate';
    default:
      return 'associate';
  }
}
