/**
 * InterviewOrb Component
 *
 * Wraps the ElevenLabs Orb component with interview-specific state management.
 * Displays an animated 3D orb that reacts to audio input/output.
 * Falls back to simple animated circle if WebGL is unavailable.
 */

'use client';

import { useMemo, useEffect, useState, useRef } from 'react';
import type { InterviewState } from '@/lib/hooks/useInterviewFlow';
import { cn } from '@/lib/utils';
import { Orb, type AgentState } from '@/components/ui/orb';
import { LiveWaveform } from '@/components/ui/live-waveform';

interface InterviewOrbProps {
  state: InterviewState;
  inputVolume: number;  // 0-1 scale
  outputVolume: number; // 0-1 scale
  isRecording: boolean;
  isMuted?: boolean;    // Whether microphone is muted
}

export function InterviewOrb({ state, inputVolume, outputVolume, isRecording, isMuted = false }: InterviewOrbProps) {
  const [showSilenceWarning, setShowSilenceWarning] = useState(false);
  const silenceStartTimeRef = useRef<number | null>(null);
  const hasSpokenRef = useRef(false);

  const agentState = useMemo<AgentState>(() => {
    switch (state) {
      case 'user-speaking':
        return 'listening';
      case 'ai-speaking':
        return 'talking';
      case 'processing':
      case 'waiting':
        return 'thinking';
      default:
        return null;
    }
  }, [state]);

  // Track silence duration - only show warning after 3 seconds of silence
  useEffect(() => {
    if (state !== 'user-speaking' || !isRecording) {
      setShowSilenceWarning(false);
      silenceStartTimeRef.current = null;
      hasSpokenRef.current = false;
      return;
    }

    if (inputVolume > SILENCE_THRESHOLD) {
      // User is speaking
      hasSpokenRef.current = true;
      silenceStartTimeRef.current = null;
      setShowSilenceWarning(false);
    } else {
      // Silence detected
      if (hasSpokenRef.current) {
        // Only track silence if user has spoken at least once
        if (silenceStartTimeRef.current === null) {
          silenceStartTimeRef.current = Date.now();
        } else {
          const silenceDuration = Date.now() - silenceStartTimeRef.current;
          if (silenceDuration >= 3000) {
            setShowSilenceWarning(true);
          }
        }
      }
    }
  }, [state, isRecording, inputVolume]);

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative h-72 w-72 sm:h-80 sm:w-80">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-slate-200 via-slate-100 to-slate-200 dark:from-slate-800 dark:via-slate-900 dark:to-slate-800 p-[3px] shadow-[0_12px_30px_rgba(15,23,42,0.2)]">
          <div className="h-full w-full overflow-hidden rounded-full bg-background/80 shadow-[inset_0_0_20px_rgba(15,23,42,0.12)] dark:shadow-[inset_0_0_25px_rgba(0,0,0,0.4)]">
            <Orb
              className="h-full w-full"
              agentState={agentState}
              volumeMode="manual"
              manualInput={isMuted ? 0 : inputVolume}
              manualOutput={outputVolume}
              colors={['#CADCFC', '#A0B9D1']}
              seed={42}
            />
          </div>
        </div>
      </div>

      {/* State Indicator */}
      <div className="mt-4 text-center">
        <p className="text-sm font-medium text-slate-700">
          {state === 'initializing' && 'Starting interview...'}
          {state === 'connecting' && 'Connecting...'}
          {state === 'ready' && 'Ready to start'}
          {state === 'ai-speaking' && 'AI is asking a question...'}
          {state === 'user-speaking' && 'Speak now - I\'m listening'}
          {state === 'processing' && 'AI is thinking...'}
          {state === 'waiting' && 'AI is thinking...'}
          {state === 'completed' && 'Interview completed'}
          {state === 'error' && 'An error occurred'}
        </p>
      </div>
    </div>
  );
}

const SILENCE_THRESHOLD = 0.01;
