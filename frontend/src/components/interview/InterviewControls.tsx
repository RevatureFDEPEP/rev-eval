/**
 * InterviewControls Component
 *
 * Provides control buttons for the interview:
 * - Start Interview
 * - Stop Speaking
 * - End Interview (with confirmation)
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Mic, MicOff, Play, X } from 'lucide-react';
import type { InterviewState } from '@/lib/hooks/useInterviewFlow';
import { cn } from '@/lib/utils';

interface InterviewControlsProps {
  state: InterviewState;
  isRecording: boolean;
  hasPermission: boolean;
  isMuted?: boolean;
  onStart: () => void;
  onStopSpeaking: () => void;
  onEnd: () => void;
  onRequestPermission: () => void;
  onToggleMute?: () => void;
}

export function InterviewControls({
  state,
  isRecording,
  hasPermission,
  isMuted = false,
  onStart,
  onStopSpeaking,
  onEnd,
  onRequestPermission,
  onToggleMute,
}: InterviewControlsProps) {
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const canStart = state === 'initializing' || state === 'ready';
  const canStopSpeaking = state === 'user-speaking' && isRecording;
  const canEnd = state !== 'initializing' && state !== 'completed' && state !== 'error';
  const canMute = isRecording && onToggleMute;

  return (
    <div className="flex flex-wrap items-center justify-center gap-3">
      {/* Start Interview - will request permission automatically */}
      {canStart && (
        <Button
          onClick={onStart}
          size="lg"
          className="gap-2 bg-blue-600 hover:bg-blue-700"
        >
          <Play className="h-5 w-5" />
          Start Interview
        </Button>
      )}

      {/* Recording Indicator */}
      {isRecording && (
        <div className="flex items-center gap-2 rounded-full bg-green-100 px-4 py-2">
          <div className="h-3 w-3 animate-pulse rounded-full bg-green-600" />
          <span className="text-sm font-medium text-green-700">
            Listening... Click &quot;I&apos;m Done Speaking&quot; when finished
          </span>
        </div>
      )}

      {/* Stop Speaking Button */}
      {canStopSpeaking && (
        <Button
          onClick={onStopSpeaking}
          size="lg"
          variant="outline"
          className="gap-2 border-green-600 text-green-700 hover:bg-green-50"
        >
          <MicOff className="h-5 w-5" />
          I'm Done Speaking
        </Button>
      )}

      {/* Mute Button */}
      {canMute && (
        <Button
          onClick={onToggleMute}
          size="lg"
          variant="outline"
          className={cn(
            "gap-2",
            isMuted
              ? "border-red-600 bg-red-50 text-red-700 hover:bg-red-100"
              : "border-slate-600 text-slate-700 hover:bg-slate-50"
          )}
        >
          {isMuted ? (
            <>
              <MicOff className="h-5 w-5 text-red-600" />
              <span className="font-semibold">MUTED</span>
            </>
          ) : (
            <>
              <Mic className="h-5 w-5" />
              Mute
            </>
          )}
        </Button>
      )}

      {/* End Interview */}
      {canEnd && (
        <Button
          onClick={() => setShowEndConfirm(true)}
          variant="destructive"
          className="gap-2"
        >
          <X className="h-4 w-4" />
          End Interview
        </Button>
      )}

      {/* End Interview Confirmation Dialog */}
      <AlertDialog open={showEndConfirm} onOpenChange={setShowEndConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>End Interview?</AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                Are you sure you want to end the interview? This action cannot be undone.
                Your responses will be submitted for evaluation.
              </p>
              <p className="font-medium text-amber-700 dark:text-amber-500">
                ⚠️ Warning: If you end the interview yourself before all questions are answered,
                you will receive a lower score because you didn&apos;t answer all the questions.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continue Interview</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowEndConfirm(false);
                onEnd();
              }}
              className="bg-red-600 hover:bg-red-700"
            >
              End Interview
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
