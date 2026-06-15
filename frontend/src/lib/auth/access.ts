/**
 * Pure role-based route access rules, shared by the Edge middleware and unit
 * tests. No next/server imports here so it runs in plain Node under vitest.
 *
 * Security note: this is one half of the server-side gate (the middleware runs
 * it at the edge; each /admin page re-checks via getSession). Client-side
 * conditional rendering of nav links is a UX affordance only — never the gate.
 */

/** Route prefix -> roles allowed to enter it (verified JWT role claim). */
export const roleProtectedRoutes: Record<string, string[]> = {
  // /admin is TRAINER-only to match the W4-F3 backend gate (require_trainer:
  // ADMIN gets 403). Keeping the frontend gate identical means an ADMIN is
  // redirected away rather than landing on a page whose data calls 403.
  '/admin': ['TRAINER'],
  '/trainer': ['TRAINER', 'ADMIN'],
  '/participant': ['PARTICIPANT'],
  '/dashboard': ['TRAINER', 'PARTICIPANT', 'ADMIN'],
};

export type AccessDecision = 'allow' | 'forbidden';

/**
 * Decide whether `role` may enter `pathname`. Unprotected paths are allowed;
 * a protected prefix allows only its listed roles, everything else forbidden.
 */
export function resolveAccess(pathname: string, role: string): AccessDecision {
  const entry = Object.entries(roleProtectedRoutes).find(([prefix]) =>
    pathname.startsWith(prefix),
  );
  if (!entry) return 'allow';
  const [, allowedRoles] = entry;
  return allowedRoles.includes(role.toUpperCase()) ? 'allow' : 'forbidden';
}
