/**
 * Next.js API Route: Trainer Tests
 *
 * BFF extracts JWT from WorkOS session and forwards to API Gateway
 */

import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@workos-inc/authkit-nextjs';

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    console.log('🔄 [Next.js API] Trainer tests request received');

    // Get the session using WorkOS withAuth
    const { user, accessToken } = await withAuth();

    if (!user || !accessToken) {
      console.error('❌ [Next.js API] No authenticated user or access token');
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    console.log('🔑 [Next.js API] Token extracted from session');

    // Forward to API Gateway with Bearer token
    const response = await fetch(`${API_GATEWAY_URL}/v1/api/dashboard/trainer/tests`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    console.log(`🌐 [Next.js API] API Gateway response: ${response.status}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ [Next.js API] API Gateway error:', errorText);
      return NextResponse.json(
        { error: 'Failed to fetch trainer tests' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('✅ [Next.js API] Successfully fetched trainer tests');

    return NextResponse.json(data);

  } catch (error: any) {
    console.error('❌ [Next.js API] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
