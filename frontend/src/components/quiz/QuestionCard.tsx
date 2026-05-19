/**
 * Question Card Component
 *
 * Wrapper for individual questions with type-specific rendering.
 * Shows question number, difficulty, and dynamically renders the appropriate question component.
 */

'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { QuizQuestion } from '@/lib/api/types';
import { MCQQuestion } from './MCQQuestion';
import { MultiQuestion } from './MultiQuestion';
import { TrueFalseQuestion } from './TrueFalseQuestion';
import { cn } from '@/lib/utils';

type QuestionResponse = number | number[] | boolean;

interface QuestionCardProps {
  question: QuizQuestion;
  questionNumber: number;
  selectedAnswer: QuestionResponse | null;  // Union type for all question types
  onAnswerChange: (answer: QuestionResponse) => void;
}

export function QuestionCard({
  question,
  questionNumber,
  selectedAnswer,
  onAnswerChange,
}: QuestionCardProps) {
  const selectionInfo = () => {
    switch (question.question_type) {
      case 'mcq':
        return { label: 'Single Answer', hint: 'Select the one best option.' };
      case 'multi':
        return { label: 'Multiple Answers', hint: 'Select all options that apply.' };
      case 'true_false':
        return { label: 'True or False', hint: 'Choose whether the statement is correct.' };
      default:
        return { label: 'Question', hint: '' };
    }
  };

  const { label, hint } = selectionInfo();

  // Get difficulty badge color
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-green-100 text-green-700 hover:bg-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200';
      case 'hard':
        return 'bg-red-100 text-red-700 hover:bg-red-200';
      default:
        return 'bg-slate-100 text-slate-700 hover:bg-slate-200';
    }
  };

  // Render the appropriate question component based on type
  const renderQuestion = () => {
    switch (question.question_type) {
      case 'mcq':
        return (
          <MCQQuestion
            question={question}
            selectedAnswer={typeof selectedAnswer === 'number' ? selectedAnswer : null}
            onAnswerChange={(optionId) => onAnswerChange(optionId)}
          />
        );

      case 'multi':
        return (
          <MultiQuestion
            question={question}
            selectedAnswers={Array.isArray(selectedAnswer) ? selectedAnswer : []}
            onAnswerChange={(optionIds) => onAnswerChange(optionIds)}
          />
        );

      case 'true_false':
        return (
          <TrueFalseQuestion
            question={question}
            selectedAnswer={typeof selectedAnswer === 'boolean' ? selectedAnswer : null}
            onAnswerChange={(answer) => onAnswerChange(answer)}
          />
        );

      default:
        return <div className="text-sm text-red-600">Unknown question type</div>;
    }
  };

  return (
    <Card className="border-slate-200 shadow-md">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="rounded-full bg-blue-100 px-3 py-1 text-blue-700">
              Q{questionNumber}
            </Badge>
            <Badge variant="secondary" className={cn('capitalize', getDifficultyColor(question.difficulty))}>
              {question.difficulty}
            </Badge>
          </div>
        </div>
        <p className="mt-4 text-base leading-relaxed text-slate-900">
          {question.question_text}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="border-blue-200 bg-blue-50 text-xs font-semibold uppercase tracking-wide text-blue-700">
            {label}
          </Badge>
          {hint && <span className="text-xs text-slate-600">{hint}</span>}
        </div>
      </CardHeader>

      <CardContent>{renderQuestion()}</CardContent>
    </Card>
  );
}
