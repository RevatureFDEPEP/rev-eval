/**
 * InterviewInterface Component
 *
 * Main interview UI that orchestrates:
 * - ElevenLabs Orb visualization
 * - WebSocket communication with backend
 * - Audio recording and playback
 * - Live transcript display
 * - Timer and controls
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { AlertCircle, CheckCircle2, MessageSquare, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { useInterviewFlow } from '@/lib/hooks/useInterviewFlow';
import { InterviewOrb } from './InterviewOrb';
import { LiveTranscript } from './LiveTranscript';
import { InterviewControls } from './InterviewControls';
import { ConnectionStatus } from './ConnectionStatus';
import { LiveWaveform } from '@/components/ui/live-waveform';

interface InterviewInterfaceProps {
  testId: number;
  testName: string;
  submissionId: number;
}

export function InterviewInterface({
  testId,
  testName,
  submissionId,
}: InterviewInterfaceProps) {
  const router = useRouter();
  const [instructionsOpen, setInstructionsOpen] = useState<string | undefined>('instructions');
  const [transcriptCollapsed, setTranscriptCollapsed] = useState(false);

  const handleComplete = useCallback(() => {
    console.log('🎉 Interview completed');
    // Don't redirect automatically - show completion screen and let user click button
  }, []);

  const {
    interviewState,
    messages,
    connectionState,
    inputVolume,
    outputVolume,
    isRecording,
    hasPermission,
    isMuted,
    startInterview,
    stopSpeaking,
    endInterview,
    toggleMute,
    error,
  } = useInterviewFlow({
    submissionId,
    onComplete: handleComplete,
  });

  const handleStart = async () => {
    console.log('🎯 START BUTTON CLICKED!');
    console.log('🎯 Current state:', interviewState);
    console.log('🎯 Has permission:', hasPermission);
    try {
      console.log('🎯 Calling startInterview()...');
      await startInterview();
      console.log('🎯 startInterview() completed');
    } catch (err) {
      console.error('🎯 Failed to start interview:', err);
      toast.error('Failed to start interview');
    }
  };

  const handleRequestPermission = async () => {
    toast.info('Please allow microphone access to continue');
  };

  // Warn user if they try to leave during an active interview
  useEffect(() => {
    const shouldWarn = 
      interviewState !== 'completed' && 
      interviewState !== 'error' && 
      interviewState !== 'initializing';
    
    if (!shouldWarn) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = 'You are leaving the interview. Your progress may be lost and the interview may be marked as abandoned. Are you sure you want to leave?';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [interviewState]);

  // Log component mount and state changes
  console.log('🔍 InterviewInterface render - state:', interviewState, 'hasPermission:', hasPermission);

  // Show completion state
  if (interviewState === 'completed') {
    return (
      <div className="flex min-h-[600px] items-center justify-center">
        <Card className="w-full max-w-2xl border-green-200 bg-green-50/50">
          <CardHeader className="text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="flex size-16 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="size-10 text-green-600" />
              </div>
              <div>
                <CardTitle className="text-2xl text-green-900">Interview Completed!</CardTitle>
                <CardDescription className="mt-2 text-base text-green-700">
                  Your responses have been submitted for evaluation
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-green-200 bg-white p-4">
              <p className="text-sm text-slate-700">
                Thank you for completing the interview. Your responses have been recorded and will be reviewed by our team.
                You can expect feedback within 24-48 hours.
              </p>
            </div>
            <div className="flex justify-center gap-3 pt-4">
              <Button
                onClick={() => router.push('/participant/tests')}
                className="bg-green-600 hover:bg-green-700"
                size="lg"
              >
                Back to My Tests
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <div className="flex justify-end">
        <ConnectionStatus state={connectionState} />
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Instructions Card - Always visible, collapsible, state persists */}
      <Accordion 
        type="single" 
        collapsible 
        value={instructionsOpen}
        onValueChange={setInstructionsOpen}
        className="w-full"
      >
        <AccordionItem value="instructions" className="border-blue-200 bg-blue-50 rounded-lg px-4">
          <AccordionTrigger className="text-blue-900 font-semibold hover:no-underline">
            Before You Begin
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4 pt-2">
              <ul className="space-y-2 text-sm text-blue-800">
                <li className="flex items-start gap-2">
                  <span className="mt-0.5">🎤</span>
                  <span>Make sure you&apos;re in a quiet environment with a working microphone</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5">🔊</span>
                  <span>Ensure your speakers or headphones are working properly</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5">💬</span>
                  <span>Speak clearly and naturally - the AI will ask follow-up questions</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-0.5">🎯</span>
                  <span>The interview will continue until all questions are answered</span>
                </li>
              </ul>
              
              <div className="border-t border-blue-200 pt-4">
                <h4 className="mb-2 text-sm font-semibold text-blue-900">Tips</h4>
                {testName && (
                  <p className="mb-2 text-xs text-blue-700">Interview: {testName}</p>
                )}
                <ul className="space-y-1.5 text-xs text-blue-800">
                  <li>• Take your time to think before responding</li>
                  <li>• Speak clearly and at a normal pace</li>
                  <li>• Provide detailed examples when possible</li>
                  <li>• Don&apos;t worry about perfect grammar - be natural</li>
                </ul>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Main Interview Area */}
      <div className="flex gap-6">
        {/* Left Column: Orb + Controls */}
        <div className={transcriptCollapsed ? 'flex-1' : 'flex-1 lg:flex-none lg:w-auto'}>
          <div className="space-y-6 flex flex-col">
            <Card className="border-slate-200 flex flex-col" style={{ minHeight: '500px' }}>
              <CardContent className="flex items-center justify-center py-8 flex-1">
                <InterviewOrb
                  state={interviewState}
                  inputVolume={inputVolume}
                  outputVolume={outputVolume}
                  isRecording={isRecording}
                  isMuted={isMuted}
                />
              </CardContent>
            </Card>

            {/* Waveform Visualization - Separate box when user is speaking */}
            {interviewState === 'user-speaking' && (
              <Card className="border-slate-200">
                <CardContent className="py-6">
                  <div className="flex flex-col items-center gap-3">
                    {(() => {
                      // Calculate silence warning (same logic as InterviewOrb)
                      const SILENCE_THRESHOLD = 0.01;
                      const showWarning = inputVolume <= SILENCE_THRESHOLD && isRecording;
                      return showWarning ? (
                        <div className="flex items-center justify-center text-[11px] text-slate-500">
                          <span className="font-medium">🔇 Speak louder</span>
                        </div>
                      ) : null;
                    })()}
                    <div className="relative h-20 w-full overflow-hidden rounded-lg border border-slate-200/60 bg-slate-50/80 shadow-inner dark:border-slate-700 dark:bg-slate-800/80">
                      <LiveWaveform
                        active={isRecording && !isMuted}
                        barWidth={5}
                        barGap={2}
                        barRadius={8}
                        barColor={isMuted ? "#94a3b8" : "#10b981"}
                        fadeEdges
                        fadeWidth={48}
                        sensitivity={0.8}
                        smoothingTimeConstant={0.85}
                        mode="static"
                        className="w-full"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <InterviewControls
              state={interviewState}
              isRecording={isRecording}
              hasPermission={hasPermission}
              isMuted={isMuted}
              onStart={handleStart}
              onStopSpeaking={stopSpeaking}
              onEnd={endInterview}
              onRequestPermission={handleRequestPermission}
              onToggleMute={toggleMute}
            />
          </div>
        </div>

        {/* Right Column: Transcript - collapsible */}
        {transcriptCollapsed ? (
          <div className="flex items-start pt-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setTranscriptCollapsed(false)}
              className="rounded-full shadow-sm hover:shadow-md transition-shadow"
              title="Show transcript"
            >
              <MessageSquare className="h-5 w-5" />
            </Button>
          </div>
        ) : (
          <div className="flex-1 min-w-0">
            <div className="h-[500px] relative">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTranscriptCollapsed(true)}
                className="absolute top-2 right-2 z-10 h-8 w-8 rounded-full bg-white/90 shadow-sm hover:bg-white"
                title="Hide transcript"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <LiveTranscript messages={messages} className="h-full" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
