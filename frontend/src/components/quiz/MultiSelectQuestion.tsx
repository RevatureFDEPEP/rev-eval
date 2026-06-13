/**
 * Multi-Select Question (checkbox group).
 *
 * Renders a `multi` ParticipantQuestion. Selection is stored as an array of
 * option_ids to match the TestRunner answers Map<string, number[]>.
 */

'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ParticipantQuestion } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface MultiSelectQuestionProps {
  question: ParticipantQuestion;
  selected: number[]; // option_ids
  onChange: (optionIds: number[]) => void;
  disabled?: boolean; // locked (submitting/submitted) or reviewing an answered question
}

export function MultiSelectQuestion({
  question,
  selected,
  onChange,
  disabled = false,
}: MultiSelectQuestionProps) {
  if (!question.options || question.options.length === 0) {
    return <div className="text-sm text-red-600">Error: No options available</div>;
  }

  const toggleOption = (optionId: number) => {
    if (selected.includes(optionId)) {
      onChange(selected.filter((id) => id !== optionId));
    } else {
      onChange([...selected, optionId]);
    }
  };

  return (
    <div className="space-y-3">
      {question.options.map((option) => {
        const isChecked = selected.includes(option.option_id);

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
              disabled={disabled}
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
