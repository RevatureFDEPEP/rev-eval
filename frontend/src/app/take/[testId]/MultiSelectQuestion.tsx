'use client';

import { TmsQuestion } from '@/lib/api/types';

interface MultiSelectQuestionProps {
  question: TmsQuestion;
  selectedAnswers: number[];
  onAnswerChange: (optionIds: number[]) => void;
}

export function MultiSelectQuestion({
  question,
  selectedAnswers,
  onAnswerChange,
}: MultiSelectQuestionProps) {
  function toggle(optionId: number) {
    if (selectedAnswers.includes(optionId)) {
      onAnswerChange(selectedAnswers.filter((id) => id !== optionId));
    } else {
      onAnswerChange([...selectedAnswers, optionId]);
    }
  }

  return (
    <fieldset className="space-y-3">
      <legend className="sr-only">Select all that apply</legend>
      <p className="text-xs text-slate-500">Select all that apply</p>
      {question.options?.map((option) => {
        const checked = selectedAnswers.includes(option.option_id);
        return (
          <label
            key={option.option_id}
            className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors ${
              checked
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            <input
              type="checkbox"
              value={option.option_id}
              checked={checked}
              onChange={() => toggle(option.option_id)}
              className="mt-0.5 shrink-0 accent-blue-600"
            />
            <span className="text-sm text-slate-800">{option.text}</span>
          </label>
        );
      })}
    </fieldset>
  );
}
