import { NextResponse } from 'next/server';
import { getSession } from '@/lib/session';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

interface UserServiceUser {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  role: string;
  organization_id?: string | null;
}

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const response = await fetch(`${API_GATEWAY_URL}/v1/api/auth/me`, {
    headers: { Authorization: `Bearer ${session.token}` },
    cache: 'no-store',
  });

  if (!response.ok) {
    return NextResponse.json({ error: 'Failed to load profile' }, { status: response.status });
  }

  const profile = (await response.json()) as UserServiceUser;

  return NextResponse.json({
    id: profile.id,
    email: profile.email,
    firstName: profile.first_name ?? undefined,
    lastName: profile.last_name ?? undefined,
    fullName: profile.full_name ?? undefined,
    role: profile.role,
    organizationId: profile.organization_id ?? undefined,
  });
}
