/**
 * TrueFalseQuestion — radio-group leaf for option-less `true_false` questions.
 *
 * `true_false` docs are canonically stored with `correct_answers: [true|false]`
 * and NO `options` array (W2-F6 authoring builds them this way), so the
 * options-based SingleSelectQuestion renders "No options available" for them
 * (W5-F3). This widget synthesizes the True/False control instead.
 *
 * To keep the take flow's uniform `Map<string, number[]>` answer shape, the
 * choice is encoded as a one-element option_id array: True → [1], False → [0].
 * Server scoring is exact set-equality (`exact_match`), and Python treats
 * `True == 1` / `False == 0`, so {1} == {true} and {0} == {false} — the stored
 * boolean `correct_answers` score correctly with no backend change.
 */
'use client';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import type { SanitizedQuestion } from '@/lib/api/types';
import { cn } from '@/lib/utils';

/** option_id encoding for the boolean choice (see module doc). */
const TRUE_ID = 1;
const FALSE_ID = 0;

interface TrueFalseQuestionProps {
  question: SanitizedQuestion;
  selected: number[];
  onChange: (optionIds: number[]) => void;
  /** Disable selection (W3-F4): exam locked/submitting, or reviewing an answered question. */
  disabled?: boolean;
  /** id of the rendered question text — ties the group to its label (W3-F7 item 7). */
  labelledBy?: string;
}

const CHOICES: ReadonlyArray<{ id: number; text: string }> = [
  { id: TRUE_ID, text: 'True' },
  { id: FALSE_ID, text: 'False' },
];

export function TrueFalseQuestion({
  question,
  selected,
  onChange,
  disabled = false,
  labelledBy,
}: TrueFalseQuestionProps) {
  const current = selected.length > 0 ? selected[0] : null;

  return (
    <RadioGroup
      key={question.id}
      disabled={disabled}
      aria-disabled={disabled}
      aria-labelledby={labelledBy}
      value={current !== null ? current.toString() : ''}
      onValueChange={(value) => {
        const parsed = Number.parseInt(value, 10);
        if (!Number.isNaN(parsed)) {
          onChange([parsed]);
        }
      }}
      className="space-y-3"
    >
      {CHOICES.map((choice) => (
        <div
          key={choice.id}
          className={cn(
            'flex items-center space-x-3 rounded-xl border border-slate-200 p-4 transition-all hover:border-blue-200 hover:bg-blue-50/40',
            current === choice.id &&
              'border-blue-400 bg-blue-50 text-slate-900 shadow-sm'
          )}
        >
          <RadioGroupItem
            value={choice.id.toString()}
            id={`${question.id}-tf-${choice.id}`}
            className="size-5 border-2"
          />
          <Label
            htmlFor={`${question.id}-tf-${choice.id}`}
            className="flex-1 cursor-pointer text-base leading-relaxed"
          >
            {choice.text}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}
