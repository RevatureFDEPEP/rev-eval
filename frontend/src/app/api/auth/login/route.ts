import { NextRequest, NextResponse } from 'next/server';
import { decodeJwt } from 'jose';
import { AUTH_COOKIE } from '@/lib/session';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

export async function POST(request: NextRequest) {
  let body: { email?: string; password?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body.email || !body.password) {
    return NextResponse.json({ error: 'Email and password required' }, { status: 400 });
  }

  const upstream = await fetch(`${API_GATEWAY_URL}/v1/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: body.email, password: body.password }),
  });

  const text = await upstream.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!upstream.ok) {
    return NextResponse.json(data ?? { error: 'Login failed' }, { status: upstream.status });
  }

  const payload = data as { access_token?: string; user?: unknown };
  if (!payload.access_token) {
    return NextResponse.json({ error: 'No access_token in user-service response' }, { status: 502 });
  }

  let maxAge = 60 * 60; // default 1h matches user-service JWT_EXPIRY_MINUTES
  try {
    const claims = decodeJwt(payload.access_token);
    if (typeof claims.exp === 'number') {
      const seconds = claims.exp - Math.floor(Date.now() / 1000);
      if (seconds > 0) maxAge = seconds;
    }
  } catch {
    // fall back to default
  }

  const response = NextResponse.json({ user: payload.user });
  response.cookies.set(AUTH_COOKIE, payload.access_token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: true,
    path: '/',
    maxAge,
  });
  return response;
}
