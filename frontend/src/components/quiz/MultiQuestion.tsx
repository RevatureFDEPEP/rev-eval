/**
 * Multi-Select Question Component
 *
 * Multiple choice question with multiple correct answers (checkboxes).
 */

'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { QuizQuestion } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface MultiQuestionProps {
  question: QuizQuestion;
  selectedAnswers: number[];  // Array of option_ids
  onAnswerChange: (optionIds: number[]) => void;
}

export function MultiQuestion({ question, selectedAnswers, onAnswerChange }: MultiQuestionProps) {
  if (!question.options || question.options.length === 0) {
    return <div className="text-sm text-red-600">Error: No options available</div>;
  }

  const toggleOption = (optionId: number) => {
    if (selectedAnswers.includes(optionId)) {
      // Remove if already selected
      onAnswerChange(selectedAnswers.filter((id) => id !== optionId));
    } else {
      // Add if not selected
      onAnswerChange([...selectedAnswers, optionId]);
    }
  };

  return (
    <div className="space-y-3">
      {question.options.map((option) => {
        const isChecked = selectedAnswers.includes(option.option_id);

        return (
          <div
            key={option.option_id}
            className={cn(
              'flex items-center space-x-3 rounded-xl border border-slate-200 p-4 transition-all hover:border-blue-200 hover:bg-blue-50/40',
              isChecked && 'border-blue-400 bg-blue-50 text-slate-900 shadow-sm'
            )}
          >
            <Checkbox
              id={`option-${option.option_id}`}
              checked={isChecked}
              onCheckedChange={() => toggleOption(option.option_id)}
              className="size-5 border-2"
            />
            <Label
              htmlFor={`option-${option.option_id}`}
              className="flex-1 cursor-pointer text-base leading-relaxed"
            >
              {option.text}
            </Label>
          </div>
        );
      })}
    </div>
  );
}
