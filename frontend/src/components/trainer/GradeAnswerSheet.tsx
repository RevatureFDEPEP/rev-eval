'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import { gradeAnswer, type PendingAnswer } from '@/lib/api';

interface GradeAnswerSheetProps {
  answer: PendingAnswer | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGraded?: () => void;
}

/**
 * Trainer surface to manually grade one free-text answer (W5-F1): shows the
 * question prompt, the candidate's submission and the sample answer, and
 * submits a 0..1 score + optional feedback.
 */
export function GradeAnswerSheet({
  answer,
  open,
  onOpenChange,
  onGraded,
}: GradeAnswerSheetProps) {
  const [score, setScore] = useState('');
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Reset the form whenever a different answer is opened.
    setScore('');
    setFeedback('');
  }, [answer?.answer_id]);

  if (!answer) return null;

  const submission = (answer.submitted_answers ?? [])
    .map((a) => String(a))
    .join('\n');

  const handleSubmit = async () => {
    const value = Number(score);
    if (Number.isNaN(value) || value < 0 || value > 1) {
      toast.error('Score must be a number between 0 and 1');
      return;
    }
    setSubmitting(true);
    try {
      await gradeAnswer(answer.session_id, answer.question_index, {
        score: value,
        feedback: feedback.trim() || null,
      });
      toast.success('Answer graded');
      onGraded?.();
      onOpenChange(false);
    } catch {
      toast.error('Failed to grade answer');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetTitle>Grade free-text answer</SheetTitle>

        <div className="mt-4 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                {answer.test_name ?? `Test #${answer.test_id}`} · participant{' '}
                {answer.user_id}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <Label className="text-muted-foreground">Question</Label>
                <p className="whitespace-pre-wrap">
                  {answer.question_text ?? answer.question_id}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Candidate answer</Label>
                <p className="whitespace-pre-wrap">{submission || '(empty)'}</p>
              </div>
              {answer.sample_answer && (
                <div>
                  <Label className="text-muted-foreground">Sample answer</Label>
                  <p className="whitespace-pre-wrap">{answer.sample_answer}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-2">
            <Label htmlFor="grade-score">Score (0 to 1)</Label>
            <Input
              id="grade-score"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={score}
              onChange={(e) => setScore(e.target.value)}
              placeholder="e.g. 0.75"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="grade-feedback">Feedback (optional)</Label>
            <Textarea
              id="grade-feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={4}
            />
          </div>

          <Button onClick={handleSubmit} disabled={submitting} className="w-full">
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Submit grade
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
