import { NextResponse } from 'next/server';
import { AUTH_COOKIE } from '@/lib/session';

async function handle() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(AUTH_COOKIE, '', {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 0,
  });
  return response;
}

export const GET = handle;
export const POST = handle;
