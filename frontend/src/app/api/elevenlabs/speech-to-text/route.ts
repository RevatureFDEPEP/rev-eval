/**
 * Speech-to-Text API Route (BFF Pattern)
 *
 * Transcribes audio to text using ElevenLabs API.
 * This route runs server-side to keep the API key secure.
 *
 * POST /api/elevenlabs/speech-to-text
 * Body: FormData with 'audio' file
 * Response: { text: string, confidence?: number }
 */

import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Parse form data
    const formData = await request.formData();
    const audioFile = formData.get('audio') as File;

    if (!audioFile) {
      return NextResponse.json(
        { error: 'Audio file is required' },
        { status: 400 }
      );
    }

    // Validate API key
    const apiKey = process.env.ELEVENLABS_API_KEY;
    if (!apiKey) {
      console.error('❌ ELEVENLABS_API_KEY not configured');
      return NextResponse.json(
        { error: 'ElevenLabs API key not configured' },
        { status: 500 }
      );
    }

    console.log('🎙️ Transcribing audio:', {
      fileName: audioFile.name,
      fileSize: audioFile.size,
      fileType: audioFile.type,
    });

    // Convert File to Buffer for ElevenLabs API
    const arrayBuffer = await audioFile.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Create multipart/form-data manually for Node.js
    // ElevenLabs API expects multipart/form-data with the audio file and model_id
    const boundary = `----WebKitFormBoundary${Math.random().toString(36).substring(2, 15)}`;
    const formDataParts: Buffer[] = [];
    
    // Add model_id field (required by ElevenLabs API)
    const modelId = process.env.NEXT_PUBLIC_ELEVENLABS_STT_MODEL_ID || "scribe_v1";
    formDataParts.push(Buffer.from(`--${boundary}\r\n`));
    formDataParts.push(Buffer.from(`Content-Disposition: form-data; name="model_id"\r\n\r\n`));
    formDataParts.push(Buffer.from(modelId));
    formDataParts.push(Buffer.from(`\r\n`));
    
    // Add file field - ElevenLabs expects field name "file"
    formDataParts.push(Buffer.from(`--${boundary}\r\n`));
    formDataParts.push(Buffer.from(`Content-Disposition: form-data; name="file"; filename="${audioFile.name || 'recording.webm'}"\r\n`));
    formDataParts.push(Buffer.from(`Content-Type: ${audioFile.type || 'audio/webm'}\r\n\r\n`));
    formDataParts.push(buffer);
    formDataParts.push(Buffer.from(`\r\n--${boundary}--\r\n`));
    
    const formDataBuffer = Buffer.concat(formDataParts);

    // Transcribe audio using ElevenLabs Speech-to-Text API
    const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
      method: 'POST',
      headers: {
        'xi-api-key': apiKey,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
      },
      body: formDataBuffer,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `ElevenLabs API error: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`
      );
    }

    const result = await response.json();

    console.log('✅ Transcription successful:', {
      textLength: result.text?.length || 0,
    });

    // Return transcript
    return NextResponse.json({
      text: result.text || '',
      confidence: 1.0, // ElevenLabs doesn't provide confidence score
    });
  } catch (error) {
    console.error('❌ Speech-to-text error:', error);

    return NextResponse.json(
      {
        error: 'Failed to transcribe audio',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
