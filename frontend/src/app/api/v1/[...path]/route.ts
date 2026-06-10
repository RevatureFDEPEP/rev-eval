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

  const forwarded: Record<string, string> = {
    Authorization: `Bearer ${session.token}`,
    'Content-Type': 'application/json',
    // Start (or continue) the distributed trace at the browser-origin hop;
    // the BFF path bypasses nginx, so the id must be set here.
    'X-Correlation-Id':
      request.headers.get('x-correlation-id') ?? crypto.randomUUID(),
  };
  // Pass through the client's idempotency key so retry-safe writes (e.g. the
  // W3-F4 exam answer submit) stay idempotent across the BFF hop.
  const idempotencyKey = request.headers.get('idempotency-key');
  if (idempotencyKey) {
    forwarded['Idempotency-Key'] = idempotencyKey;
  }

  const response = await fetch(url.toString(), {
    method: request.method,
    headers: forwarded,
    body,
  });

  const text = await response.text();

  // 204/205 (and any empty body) must NOT carry a payload — NextResponse.json
  // would emit "null", and a body on a no-content status throws. Pass the
  // bodyless status straight through (e.g. successful DELETE -> 204).
  if (!text || response.status === 204 || response.status === 205) {
    return new NextResponse(null, { status: response.status });
  }

  let payload: unknown;
  try {
    payload = JSON.parse(text);
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
