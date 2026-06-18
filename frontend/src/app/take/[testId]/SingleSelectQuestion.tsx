'use client';

import { TmsQuestion } from '@/lib/api/types';

interface SingleSelectQuestionProps {
  question: TmsQuestion;
  selectedAnswer: number | null;
  onAnswerChange: (optionId: number) => void;
}

export function SingleSelectQuestion({
  question,
  selectedAnswer,
  onAnswerChange,
}: SingleSelectQuestionProps) {
  return (
    <fieldset className="space-y-3">
      <legend className="sr-only">Select one answer</legend>
      {question.options?.map((option) => {
        const checked = selectedAnswer === option.option_id;
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
              type="radio"
              name={`question-${question._id}`}
              value={option.option_id}
              checked={checked}
              onChange={() => onAnswerChange(option.option_id)}
              className="mt-0.5 shrink-0 accent-blue-600"
            />
            <span className="text-sm text-slate-800">{option.text}</span>
          </label>
        );
      })}
    </fieldset>
  );
}
