/**
 * Timer Component
 *
 * Displays countdown timer in top-right corner.
 * Subtle design that doesn't distract, with visual warnings at 5 min and 1 min.
 */

'use client';

import { Clock } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TimerProps {
  timeRemaining: number;  // Seconds
  formatTime: () => string;  // Formatted time string
  isWarning: boolean;  // < 5 minutes
  isCritical: boolean;  // < 1 minute
}

export function Timer({ timeRemaining, formatTime, isWarning, isCritical }: TimerProps) {
  // Determine styling based on time remaining
  const getTimerColor = () => {
    if (isCritical) {
      return 'bg-red-100 text-red-700 border-red-300 animate-pulse';
    }
    if (isWarning) {
      return 'bg-amber-100 text-amber-700 border-amber-300';
    }
    return 'bg-blue-100 text-blue-700 border-blue-300';
  };

  return (
    <div className="w-full">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge
              variant="outline"
              className={cn(
                'flex w-full items-center justify-center gap-2 px-3 py-3 text-sm font-mono font-medium shadow-sm transition-all',
                getTimerColor()
              )}
            >
              <Clock className="size-4" />
              <span>{formatTime()}</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-xs">
            <p>Time Remaining</p>
            {isCritical && <p className="text-red-600 font-medium">Test will auto-submit soon!</p>}
            {isWarning && !isCritical && <p className="text-amber-600">Please review your answers</p>}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
