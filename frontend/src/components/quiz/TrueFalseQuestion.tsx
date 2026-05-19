/**
 * True/False Question Component
 *
 * Two-button question for true/false answers.
 */

'use client';

import { Button } from '@/components/ui/button';
import { Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { QuizQuestion } from '@/lib/api/types';

interface TrueFalseQuestionProps {
  question: QuizQuestion;
  selectedAnswer: boolean | null;  // true, false, or null
  onAnswerChange: (answer: boolean) => void;
}

export function TrueFalseQuestion({ question, selectedAnswer, onAnswerChange }: TrueFalseQuestionProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <Button
        type="button"
        variant={selectedAnswer === true ? 'default' : 'outline'}
        size="lg"
        onClick={() => onAnswerChange(true)}
        className={cn(
          'h-24 text-lg font-medium transition-all',
          selectedAnswer === true && 'bg-blue-600 hover:bg-blue-700'
        )}
      >
        <Check className="mr-2 size-6" />
        True
      </Button>

      <Button
        type="button"
        variant={selectedAnswer === false ? 'default' : 'outline'}
        size="lg"
        onClick={() => onAnswerChange(false)}
        className={cn(
          'h-24 text-lg font-medium transition-all',
          selectedAnswer === false && 'bg-blue-600 hover:bg-blue-700'
        )}
      >
        <X className="mr-2 size-6" />
        False
      </Button>
    </div>
  );
}
