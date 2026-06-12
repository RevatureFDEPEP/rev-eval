import { NextResponse } from 'next/server';
import { getSession } from '@/lib/session';
import { mapUserServiceUser, type UserServiceUser } from '@/lib/auth/mapUser';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

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

  return NextResponse.json(mapUserServiceUser(profile));
}
