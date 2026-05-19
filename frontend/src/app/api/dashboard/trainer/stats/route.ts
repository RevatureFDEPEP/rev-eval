import { NextResponse } from 'next/server';
import { getSession } from '@/lib/session';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const response = await fetch(`${API_GATEWAY_URL}/v1/api/dashboard/trainer/stats`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${session.token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: 'Failed to fetch trainer stats' },
      { status: response.status },
    );
  }

  return NextResponse.json(await response.json());
}
