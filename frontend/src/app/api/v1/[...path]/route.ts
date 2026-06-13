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

  // Forward client headers generically (Idempotency-Key, If-Match, etc.) rather
  // than allow-listing one at a time. Drop hop-by-hop headers and every header we
  // re-mint below — otherwise a forwarded copy plus our own value collide into a
  // comma-joined header (e.g. "Content-Type: application/json, application/json",
  // which the downstream no longer recognises as JSON).
  const STRIP = new Set([
    'host',
    'connection',
    'content-length',
    'transfer-encoding',
    'keep-alive',
    'cookie',
    'authorization', // replaced by the Bearer token
    'content-type', // re-minted below
    'x-correlation-id', // re-minted below
  ]);
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    if (!STRIP.has(key.toLowerCase())) headers[key] = value;
  });
  headers['Authorization'] = `Bearer ${session.token}`;
  headers['Content-Type'] = 'application/json';
  headers['X-Correlation-Id'] =
    request.headers.get('x-correlation-id') ??
    crypto.randomUUID().replace(/-/g, '');

  // A connection-level failure to the gateway (down/unreachable) must surface as
  // 502, not a bare unhandled 500: the client classifies 502/503/504 as transient
  // and retries, so a brief upstream blip self-heals instead of failing the call.
  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: request.method,
      headers,
      body,
    });
  } catch {
    return NextResponse.json(
      { error: 'Upstream service unavailable' },
      { status: 502 }
    );
  }

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
