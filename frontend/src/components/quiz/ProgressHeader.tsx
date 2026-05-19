/**
 * Progress Header Component
 *
 * Shows current part, question progress, test info, and navigation buttons.
 * Displays at the top of the quiz page.
 */

'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProgressHeaderProps {
  part: 'A' | 'B';
  currentQuestionNumber: number;  // 1-based (1, 2, 3...)
  answeredCount: number;          // Number of questions answered so far
  totalQuestions: number;         // Questions in the current part
  overallQuestionCount?: number;  // Total questions across the whole quiz
  testName: string;
  testRole?: string;
  onPrevious: () => void;
  onNext: () => void;
  hasPrevious: boolean;
  hasNext: boolean;
}

export function ProgressHeader({
  part,
  currentQuestionNumber,
  answeredCount,
  totalQuestions,
  overallQuestionCount,
  testName,
  testRole,
  onPrevious,
  onNext,
  hasPrevious,
  hasNext,
}: ProgressHeaderProps) {
  const getPartColor = () => {
    return part === 'A'
      ? 'bg-blue-100 text-blue-700 border-blue-300'
      : 'bg-purple-100 text-purple-700 border-purple-300';
  };

  const progressDenominator = overallQuestionCount ?? totalQuestions;
  const progress = progressDenominator > 0
    ? Math.min(100, Math.round((answeredCount / progressDenominator) * 100))
    : 0;

  return (
    <div className="sticky top-0 z-40 border-b bg-white shadow-sm">
      <div className="container mx-auto px-4 py-4">
        {/* Test Info Row */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-slate-900">{testName}</h1>
            {testRole && (
              <Badge variant="outline" className="text-xs">
                {testRole}
              </Badge>
            )}
          </div>
        </div>

        {/* Progress and Navigation Row */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between md:gap-4">
          {/* Part Badge, Progress Text & bar */}
          <div className="flex flex-1 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                variant="outline"
                className={cn('px-3 py-1 text-sm font-medium', getPartColor())}
              >
                Part {part}
              </Badge>
              <span className="text-sm font-medium text-slate-700">
                Question {currentQuestionNumber} of {totalQuestions}
              </span>
              <span className="text-xs uppercase tracking-wide text-slate-500">
                Answered {answeredCount}/{progressDenominator} · {progress}% complete
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center gap-2 self-start md:self-auto">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onPrevious}
              disabled={!hasPrevious}
              className="gap-2"
            >
              <ChevronLeft className="size-4" />
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onNext}
              disabled={!hasNext}
              className="gap-2"
            >
              Next
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
