/**
 * Generic BFF Proxy Route
 *
 * Forwards all /api/v1/* requests to API Gateway with authentication.
 * Extracts JWT from WorkOS session and adds Bearer token header.
 */

import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@workos-inc/authkit-nextjs';

// Use API_GATEWAY_URL for server-side (Docker: api-gateway:8000, Local: localhost:8000)
const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://localhost:8000';

async function handleRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    // Await params if it's a Promise (Next.js 15+)
    const params = await Promise.resolve(context.params);
    const path = params.path?.join('/') || '';
    console.log(`🔄 [BFF Proxy] ${request.method} /v1/${path}`);

    // Get the session using WorkOS withAuth
    const { user, accessToken } = await withAuth();

    if (!user || !accessToken) {
      console.error('❌ [BFF Proxy] No authenticated user or access token');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    console.log(`🔑 [BFF Proxy] User: ${user.email}`);

    // Build the full URL
    const url = new URL(`/v1/${path}`, API_GATEWAY_URL);

    // Forward query parameters
    request.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.append(key, value);
    });

    // Get request body if present
    let body: string | undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        body = await request.text();
      } catch (e) {
        // No body or already consumed
      }
    }

    // Forward to API Gateway with Bearer token and user email
    const response = await fetch(url.toString(), {
      method: request.method,
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'X-User-Email': user.email,
        'Content-Type': 'application/json',
      },
      body,
    });

    console.log(`🌐 [BFF Proxy] API Gateway response: ${response.status}`);

    // Get response body
    const responseText = await response.text();
    let responseData;
    try {
      responseData = responseText ? JSON.parse(responseText) : null;
    } catch {
      responseData = responseText;
    }

    if (!response.ok) {
      console.error('❌ [BFF Proxy] API Gateway error:', responseData);
      return NextResponse.json(
        responseData || { error: 'Request failed' },
        { status: response.status }
      );
    }

    return NextResponse.json(responseData, { status: response.status });

  } catch (error: any) {
    console.error('❌ [BFF Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error', message: error.message },
      { status: 500 }
    );
  }
}

// Export handlers for all HTTP methods
export const GET = handleRequest;
export const POST = handleRequest;
export const PUT = handleRequest;
export const DELETE = handleRequest;
export const PATCH = handleRequest;
