/**
 * InterviewTimer Component
 *
 * Displays countdown timer for interview duration.
 * Shows warnings at 5 min and 1 min remaining.
 * Auto-ends interview when time expires.
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { Clock } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface InterviewTimerProps {
  durationSeconds: number;
  isActive: boolean;
  onTimeExpired: () => void;
  className?: string;
}

export function InterviewTimer({
  durationSeconds,
  isActive,
  onTimeExpired,
  className
}: InterviewTimerProps) {
  const [timeRemaining, setTimeRemaining] = useState(durationSeconds);

  const isWarning = timeRemaining <= 5 * 60; // 5 minutes
  const isCritical = timeRemaining <= 1 * 60; // 1 minute

  const formatTime = useCallback(() => {
    const hours = Math.floor(timeRemaining / 3600);
    const minutes = Math.floor((timeRemaining % 3600) / 60);
    const seconds = timeRemaining % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, [timeRemaining]);

  const getTimerColor = () => {
    if (isCritical) {
      return 'bg-red-100 text-red-700 border-red-300 animate-pulse';
    }
    if (isWarning) {
      return 'bg-amber-100 text-amber-700 border-amber-300';
    }
    return 'bg-slate-100 text-slate-700 border-slate-300';
  };

  // Countdown timer
  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onTimeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isActive, onTimeExpired]);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-sm font-mono font-medium shadow-sm transition-all',
              getTimerColor(),
              className
            )}
          >
            <Clock className="size-4" />
            <span>{formatTime()}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <p>Time Remaining</p>
          {isCritical && <p className="font-medium text-red-600">Interview will end soon!</p>}
          {isWarning && !isCritical && <p className="text-amber-600">Please wrap up your responses</p>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
