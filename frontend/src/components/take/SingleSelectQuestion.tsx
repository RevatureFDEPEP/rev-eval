'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import type { SanitizedQuestion } from '@/lib/api/types';

/** TRUE_FALSE carries no options from the backend; render synthesized choices.
 * TestRunner maps option_id 1→true, 2→false on submit. */
const TRUE_FALSE_OPTIONS = [
  { option_id: 1, text: 'True' },
  { option_id: 2, text: 'False' },
];

interface SingleSelectQuestionProps {
  question: SanitizedQuestion;
  selected: number[];
  onChange: (optionIds: number[]) => void;
  /** Disabled while reviewing answered history (W3-F3) or locked/submitting (W3-F4). */
  disabled?: boolean;
}

/**
 * Single-select (MCQ / TRUE_FALSE) leaf — a radio group. The selection is
 * stored as a one-element array of 1-indexed option_ids to keep a uniform
 * `Map<string, number[]>` answer shape across question types.
 */
export function SingleSelectQuestion({
  question,
  selected,
  onChange,
  disabled = false,
}: SingleSelectQuestionProps) {
  const options =
    question.type?.toLowerCase() === 'true_false' &&
    (!question.options || question.options.length === 0)
      ? TRUE_FALSE_OPTIONS
      : question.options ?? [];

  if (options.length === 0) {
    return <p className="text-sm text-red-600">No options available for this question.</p>;
  }

  const value = selected.length > 0 ? String(selected[0]) : '';

  return (
    <RadioGroup
      value={value}
      onValueChange={(v) => {
        const n = Number.parseInt(v, 10);
        if (!Number.isNaN(n)) onChange([n]);
      }}
      disabled={disabled}
      aria-disabled={disabled}
      className="space-y-2"
    >
      {options.map((opt) => {
        const id = `${question.id}-opt-${opt.option_id}`;
        return (
          <div key={opt.option_id} className="flex items-center gap-3">
            <RadioGroupItem value={String(opt.option_id)} id={id} disabled={disabled} />
            <Label htmlFor={id} className="cursor-pointer font-normal">
              {opt.text}
            </Label>
          </div>
        );
      })}
    </RadioGroup>
  );
}
