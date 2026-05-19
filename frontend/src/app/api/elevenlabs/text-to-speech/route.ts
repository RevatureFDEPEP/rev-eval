/**
 * Text-to-Speech API Route (BFF Pattern)
 *
 * Converts text to speech using ElevenLabs API.
 * This route runs server-side to keep the API key secure.
 *
 * POST /api/elevenlabs/text-to-speech
 * Body: { text: string, voice_id?: string }
 * Response: Audio stream (audio/mpeg)
 */

import { ElevenLabsClient } from '@elevenlabs/elevenlabs-js';
import { NextRequest, NextResponse } from 'next/server';

/**
 * Strip markdown formatting and emojis for natural speech
 */
function cleanTextForSpeech(text: string): string {
  return text
    // Remove markdown bold/italic
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove markdown headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove markdown lists (keep content)
    .replace(/^[\s]*[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // Remove emojis
    .replace(/[\u{1F600}-\u{1F64F}]/gu, '') // Emoticons
    .replace(/[\u{1F300}-\u{1F5FF}]/gu, '') // Misc Symbols and Pictographs
    .replace(/[\u{1F680}-\u{1F6FF}]/gu, '') // Transport and Map
    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '') // Flags
    .replace(/[\u{2600}-\u{26FF}]/gu, '')   // Misc symbols
    .replace(/[\u{2700}-\u{27BF}]/gu, '')   // Dingbats
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const { text, voice_id } = await request.json();

    if (!text) {
      return NextResponse.json(
        { error: 'Text is required' },
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

    // Initialize ElevenLabs client
    const elevenlabs = new ElevenLabsClient({
      apiKey,
    });

    // Clean markdown and emojis for natural speech
    const cleanedText = cleanTextForSpeech(text);

    // Use provided voice_id or default from env, or fallback
    // Check server-side env var first (ELEVENLABS_VOICE_ID), then client-side (NEXT_PUBLIC_ELEVENLABS_VOICE_ID)
    const voiceId =
      voice_id ||
      process.env.ELEVENLABS_VOICE_ID ||
      process.env.NEXT_PUBLIC_ELEVENLABS_VOICE_ID ||
      's3TPKV1kjDlVtZbl4Ksh';

    console.log('🎤 Converting text to speech:', {
      textLength: text.length,
      cleanedLength: cleanedText.length,
      voiceId,
    });
    console.log('🎯 Original:', text.substring(0, 150));
    console.log('🎯 Cleaned:', cleanedText.substring(0, 150));

    // Convert text to speech using Turbo v2.5 model (low latency)
    const audio = await elevenlabs.textToSpeech.convert(voiceId, {
      text: cleanedText,
      modelId: 'eleven_flash_v2_5', // Fast model for real-time applications
      voiceSettings: {
        stability: 0.5,
        similarityBoost: 0.8,
        style: 0.0,
        useSpeakerBoost: true,
      },
    });

    // Convert ReadableStream to buffer
    const reader = audio.getReader();
    const chunks: Uint8Array[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) chunks.push(value);
    }

    const audioBuffer = Buffer.concat(chunks);

    console.log('✅ Audio generated successfully:', {
      sizeBytes: audioBuffer.length,
    });

    // Return audio stream
    return new NextResponse(audioBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': audioBuffer.length.toString(),
      },
    });
  } catch (error) {
    console.error('❌ Text-to-speech error:', error);

    return NextResponse.json(
      {
        error: 'Failed to convert text to speech',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
