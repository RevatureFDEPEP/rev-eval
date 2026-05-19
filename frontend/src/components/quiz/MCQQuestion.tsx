/**
 * MCQ Question Component
 *
 * Single-select multiple choice question (radio buttons).
 */

'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { QuizQuestion } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface MCQQuestionProps {
  question: QuizQuestion;
  selectedAnswer: number | null;  // option_id or null
  onAnswerChange: (optionId: number) => void;
}

export function MCQQuestion({ question, selectedAnswer, onAnswerChange }: MCQQuestionProps) {
  if (!question.options || question.options.length === 0) {
    return <div className="text-sm text-red-600">Error: No options available</div>;
  }

  return (
    <RadioGroup
      key={question.question_id}
      value={selectedAnswer !== null ? selectedAnswer.toString() : ''}
      onValueChange={(value) => {
        const parsed = Number.parseInt(value, 10);
        if (!Number.isNaN(parsed)) {
          onAnswerChange(parsed);
        }
      }}
      className="space-y-3"
    >
      {question.options.map((option) => (
        <div
          key={option.option_id}
          className={cn(
            'flex items-center space-x-3 rounded-xl border border-slate-200 p-4 transition-all hover:border-blue-200 hover:bg-blue-50/40',
            selectedAnswer === option.option_id &&
              'border-blue-400 bg-blue-50 text-slate-900 shadow-sm'
          )}
        >
          <RadioGroupItem
            value={option.option_id.toString()}
            id={`option-${option.option_id}`}
            className="size-5 border-2"
          />
          <Label
            htmlFor={`option-${option.option_id}`}
            className="flex-1 cursor-pointer text-base leading-relaxed"
          >
            {option.text}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}
