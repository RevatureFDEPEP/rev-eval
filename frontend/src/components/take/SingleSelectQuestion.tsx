/**
 * SingleSelectQuestion — radio-group leaf for single-answer questions
 * (mcq / true_false). Selection is stored as a one-element array of option_ids
 * to keep a uniform `Map<string, number[]>` answer shape across question types.
 */
'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import type { SanitizedQuestion } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface SingleSelectQuestionProps {
  question: SanitizedQuestion;
  selected: number[];
  onChange: (optionIds: number[]) => void;
}

export function SingleSelectQuestion({
  question,
  selected,
  onChange,
}: SingleSelectQuestionProps) {
  if (!question.options || question.options.length === 0) {
    return <div className="text-sm text-red-600">Error: No options available</div>;
  }

  const current = selected.length > 0 ? selected[0] : null;

  return (
    <RadioGroup
      key={question.id}
      value={current !== null ? current.toString() : ''}
      onValueChange={(value) => {
        const parsed = Number.parseInt(value, 10);
        if (!Number.isNaN(parsed)) {
          onChange([parsed]);
        }
      }}
      className="space-y-3"
    >
      {question.options.map((option) => (
        <div
          key={option.option_id}
          className={cn(
            'flex items-center space-x-3 rounded-xl border border-slate-200 p-4 transition-all hover:border-blue-200 hover:bg-blue-50/40',
            current === option.option_id &&
              'border-blue-400 bg-blue-50 text-slate-900 shadow-sm'
          )}
        >
          <RadioGroupItem
            value={option.option_id.toString()}
            id={`${question.id}-option-${option.option_id}`}
            className="size-5 border-2"
          />
          <Label
            htmlFor={`${question.id}-option-${option.option_id}`}
            className="flex-1 cursor-pointer text-base leading-relaxed"
          >
            {option.text}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}
