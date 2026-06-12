import type { AuthUser } from './useAuth';

/** Raw user-service `/auth/me` profile payload (snake_case). */
export interface UserServiceUser {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  role: string;
  organization_id?: string | null;
}

/** Map the user-service profile payload to the client-facing AuthUser shape. */
export function mapUserServiceUser(p: UserServiceUser): AuthUser {
  return {
    id: p.id,
    email: p.email,
    firstName: p.first_name ?? undefined,
    lastName: p.last_name ?? undefined,
    fullName: p.full_name ?? undefined,
    role: p.role,
    organizationId: p.organization_id ?? undefined,
  };
}
