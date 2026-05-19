/**
 * Audio Upload API Route (BFF Pattern)
 *
 * Proxies audio upload requests from frontend to the interview service backend.
 * This follows the Backend-for-Frontend pattern to hide backend URLs from the client.
 */

import { NextRequest, NextResponse } from 'next/server';

const INTERVIEW_SERVICE_URL = process.env.INTERVIEW_SERVICE_URL || 'http://localhost:8006';

export async function POST(request: NextRequest) {
  try {
    // Get form data from frontend
    const formData = await request.formData();

    // Forward to backend interview service
    const backendUrl = `${INTERVIEW_SERVICE_URL}/v1/api/interview/upload-audio`;

    const response = await fetch(backendUrl, {
      method: 'POST',
      body: formData, // Forward formData as-is
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend upload error:', errorText);
      return NextResponse.json(
        { error: 'Failed to upload audio', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Audio upload error:', error);
    return NextResponse.json(
      { error: 'Internal server error during audio upload' },
      { status: 500 }
    );
  }
}
