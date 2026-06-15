'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { SanitizedQuestion } from '@/lib/api/types';

interface MultiSelectQuestionProps {
  question: SanitizedQuestion;
  selected: number[];
  onChange: (optionIds: number[]) => void;
  /** Disabled while reviewing answered history (W3-F3) or locked/submitting (W3-F4). */
  disabled?: boolean;
}

/**
 * Multi-select (MULTI) leaf — a checkbox group. Selected 1-indexed option_ids
 * are kept as a sorted `number[]` to match the uniform answer-Map shape and to
 * stay order-insensitive for the backend's set-based scoring.
 */
export function MultiSelectQuestion({
  question,
  selected,
  onChange,
  disabled = false,
}: MultiSelectQuestionProps) {
  const options = question.options ?? [];

  const toggle = (optionId: number, checked: boolean) => {
    const set = new Set(selected);
    if (checked) set.add(optionId);
    else set.delete(optionId);
    onChange([...set].sort((a, b) => a - b));
  };

  return (
    <div className="space-y-2">
      {options.map((opt) => {
        const id = `${question.id}-opt-${opt.option_id}`;
        return (
          <div key={opt.option_id} className="flex items-center gap-3">
            <Checkbox
              id={id}
              checked={selected.includes(opt.option_id)}
              onCheckedChange={(c) => toggle(opt.option_id, c === true)}
              disabled={disabled}
            />
            <Label htmlFor={id} className="cursor-pointer font-normal">
              {opt.text}
            </Label>
          </div>
        );
      })}
    </div>
  );
}
