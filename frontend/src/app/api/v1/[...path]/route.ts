/**
 * Generic BFF proxy: forwards /api/v1/* to the API Gateway with the
 * user-service JWT lifted from the auth cookie as a Bearer header.
 */
import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/session';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://api-gateway:8000';

async function handleRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> | { path: string[] } },
) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const params = await Promise.resolve(context.params);
  const path = params.path?.join('/') || '';
  const url = new URL(`/v1/${path}`, API_GATEWAY_URL);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });

  let body: string | undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    try {
      body = await request.text();
    } catch {
      body = undefined;
    }
  }

  const response = await fetch(url.toString(), {
    method: request.method,
    headers: {
      Authorization: `Bearer ${session.token}`,
      'Content-Type': 'application/json',
    },
    body,
  });

  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }

  return NextResponse.json(payload, { status: response.status });
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const DELETE = handleRequest;
export const PATCH = handleRequest;
