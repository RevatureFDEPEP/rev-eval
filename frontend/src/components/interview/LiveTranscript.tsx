/**
 * LiveTranscript Component
 *
 * Displays the real-time conversation transcript during the interview.
 * Shows AI questions and user responses with timestamps.
 */

'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bot, User } from 'lucide-react';
import type { InterviewMessage } from '@/lib/hooks/useInterviewWebSocket';
import { cn } from '@/lib/utils';

interface LiveTranscriptProps {
  messages: InterviewMessage[];
  className?: string;
}

export function LiveTranscript({ messages, className }: LiveTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    // Use a small delay to ensure DOM is updated
    const timeout = setTimeout(() => {
      // Try to find the ScrollArea viewport element
      const viewport = scrollRef.current?.querySelector('[data-slot="scroll-area-viewport"]') as HTMLElement;
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      } else if (scrollRef.current) {
        // Fallback to direct scroll
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, 100);

    return () => clearTimeout(timeout);
  }, [messages]);

  // Filter out system messages that are not interview_ended
  const displayMessages = messages.filter(
    (msg) => msg.role !== 'system' || msg.interview_ended
  );

  return (
    <Card className={cn('border-slate-200 bg-white flex flex-col h-full', className)}>
      <CardHeader className="pb-3 shrink-0">
        <CardTitle className="text-lg font-semibold text-slate-900">
          Live Transcript
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <ScrollArea className="h-full" ref={scrollRef}>
          <div className="px-6 pb-6">
            {displayMessages.length === 0 ? (
              <div className="flex h-full min-h-[400px] items-center justify-center text-sm text-slate-500">
                Transcript will appear here during the interview
              </div>
            ) : (
              <div className="space-y-4 py-4">
                {displayMessages.map((message, index) => (
                  <div
                    key={index}
                    className={cn(
                      'flex gap-3 rounded-lg p-3',
                      message.role === 'assistant'
                        ? 'bg-blue-50 border border-blue-200'
                        : message.role === 'user'
                          ? 'bg-green-50 border border-green-200'
                          : 'bg-slate-50 border border-slate-200'
                    )}
                  >
                    {/* Icon */}
                    <div className="shrink-0">
                      {message.role === 'assistant' ? (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600">
                          <Bot className="h-4 w-4 text-white" />
                        </div>
                      ) : message.role === 'user' ? (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-600">
                          <User className="h-4 w-4 text-white" />
                        </div>
                      ) : (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-600">
                          <Bot className="h-4 w-4 text-white" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                          {message.role === 'assistant'
                            ? 'AI Interviewer'
                            : message.role === 'user'
                              ? 'You'
                              : 'System'}
                        </span>
                        {message.error && (
                          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                            Error
                          </span>
                        )}
                      </div>
                      <p className="text-sm leading-relaxed text-slate-700 break-words">
                        {message.data}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
