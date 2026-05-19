/**
 * Question Navigation Component
 *
 * Displays question shortcuts grouped by quiz parts (Part A, Part B).
 * Clearly shows availability per part and prevents navigating to other parts.
 */

'use client';

import { QuizQuestion } from '@/lib/api/types';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface QuestionNavigationProps {
  currentPart: 'A' | 'B';
  currentQuestionId: string | null;
  partAQuestions: QuizQuestion[];
  partBQuestions: QuizQuestion[];
  answeredQuestionIds: Set<string>;
  onNavigate: (questionId: string, part: 'A' | 'B') => void;
}

export function QuestionNavigation({
  currentPart,
  currentQuestionId,
  partAQuestions,
  partBQuestions,
  answeredQuestionIds,
  onNavigate,
}: QuestionNavigationProps) {
  const sections: Array<{
    part: 'A' | 'B';
    title: string;
    questions: QuizQuestion[];
    available: boolean;
    lockedMessage?: string;
  }> = [
    {
      part: 'A',
      title: 'Part A',
      questions: partAQuestions,
      available: partAQuestions.length > 0,
    },
    {
      part: 'B',
      title: 'Part B',
      questions: partBQuestions,
      available: partBQuestions.length > 0,
      lockedMessage: 'Unlocks after you submit Part A.',
    },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-medium text-slate-700">Questions</h3>
      <TooltipProvider delayDuration={150}>
        <div className="space-y-6">
          {sections.map((section) => {
            const isCurrentPart = section.part === currentPart;
            const statusLabel = !section.available
              ? 'Waiting'
              : isCurrentPart
                ? 'In Progress'
                : section.part === 'A'
                  ? 'Completed'
                  : 'Locked';
            const statusClass = !section.available
              ? 'text-slate-300'
              : isCurrentPart
                ? 'text-blue-600'
                : section.part === 'A'
                  ? 'text-emerald-600'
                  : 'text-slate-400';

            return (
              <div key={section.part}>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {section.title}
                  </span>
                  <span className={cn('text-[10px] font-medium uppercase tracking-wide', statusClass)}>
                    {statusLabel}
                  </span>
                </div>

                {!section.available ? (
                  <div className="rounded-lg border border-dashed bg-slate-50 p-4 text-xs text-slate-500">
                    {section.lockedMessage || 'This part will unlock later in the quiz.'}
                  </div>
                ) : (
                  <div className="grid grid-cols-4 gap-2.5 sm:grid-cols-5 md:grid-cols-6">
                    {section.questions.map((question, index) => {
                      const isCurrent = isCurrentPart && currentQuestionId === question.question_id;
                      const isAnswered = answeredQuestionIds.has(question.question_id);
                      const isDisabled = !isCurrentPart;
                      const isCompletedSection = !isCurrentPart && section.part === 'A';

                      const buttonClass = cn(
                        'h-10 w-10 rounded-full border transition-all',
                        isDisabled && !isCompletedSection && 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400',
                        isDisabled && isCompletedSection && 'cursor-not-allowed border-emerald-200 bg-emerald-50 text-emerald-600',
                        !isDisabled && isCurrent &&
                          'border-blue-500 bg-blue-600 text-white shadow-[0_8px_16px_-12px_rgba(37,99,235,0.65)] hover:bg-blue-600',
                        !isDisabled && isAnswered && !isCurrent &&
                          'border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
                        !isDisabled && !isAnswered && !isCurrent &&
                          'border-slate-300 bg-white text-slate-600 hover:border-blue-200 hover:bg-blue-50'
                      );

                      const tooltipState = isDisabled
                        ? section.part === 'A'
                          ? ' • Completed'
                          : ' • Locked'
                        : isCurrent
                          ? ' • Current'
                          : isAnswered
                            ? ' • Answered'
                            : ' • Not answered';

                      const ariaState = isDisabled
                        ? section.part === 'A'
                          ? 'completed'
                          : 'locked'
                        : isAnswered
                          ? 'answered'
                          : 'not answered';

                      return (
                        <Tooltip key={question.question_id}>
                          <TooltipTrigger asChild>
                            <Button
                              type="button"
                              variant="outline"
                              size="icon"
                              disabled={isDisabled}
                              aria-label={`Go to Part ${section.part} question ${index + 1}, ${ariaState}`}
                              aria-current={isCurrent ? 'page' : undefined}
                              onClick={() => {
                                if (!isDisabled) {
                                  onNavigate(question.question_id, section.part);
                                }
                              }}
                              className={buttonClass}
                            >
                              {index + 1}
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent side="top">
                            <p>
                              Part {section.part} · Question {index + 1}{tooltipState}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </TooltipProvider>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <div className="flex items-center gap-2">
          <div className="size-4 rounded-full border-2 border-emerald-300 bg-emerald-50"></div>
          <span>Answered</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="size-4 rounded-full border-2 border-blue-600 bg-blue-600"></div>
          <span>Current</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="size-4 rounded-full border-2 border-slate-300 bg-white"></div>
          <span>Unanswered</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="size-4 rounded-full border-2 border-slate-200 bg-slate-100"></div>
          <span>Other Part</span>
        </div>
      </div>
    </div>
  );
}
