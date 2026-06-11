'use client';

import { useEffect, useRef, useState } from 'react';

export type AutosaveAnswerValue = number | number[] | boolean;

/**
 * Pure function — generates the idempotency key for a single saved answer.
 * Triple: session_id + question_id + attempt_n
 * Same triple on retry → server (or localStorage) deduplicates the save.
 */
export function makeIdempotencyKey(sessionId: string, questionId: string, attemptN: number): string {
  return `${sessionId}:${questionId}:${attemptN}`;
}

interface UseAutosaveOptions {
  sessionId: string | null;
  answers: Map<string, AutosaveAnswerValue>;
  delayMs?: number;
}

interface UseAutosaveReturn {
  isSaving: boolean;
  lastSaved: Date | null;
}

/**
 * Debounced autosave for quiz answers.
 *
 * Detects which answers changed since the last save, increments per-question
 * attempt counters, then after `delayMs` writes a draft snapshot to
 * localStorage keyed by sessionId.
 *
 * Idempotency: each entry carries `idempotency_key = session:question:attempt_n`
 * so a future server-side endpoint can deduplicate retries.
 */
export function useAutosave({
  sessionId,
  answers,
  delayMs = 400,
}: UseAutosaveOptions): UseAutosaveReturn {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptCountRef = useRef<Map<string, number>>(new Map());
  const prevAnswersRef = useRef<Map<string, AutosaveAnswerValue>>(new Map());

  useEffect(() => {
    if (!sessionId) return;

    // Identify answers that changed since last save
    const changed: string[] = [];
    answers.forEach((value, key) => {
      const prev = prevAnswersRef.current.get(key);
      if (prev === undefined || JSON.stringify(prev) !== JSON.stringify(value)) {
        changed.push(key);
      }
    });

    if (changed.length === 0) return;

    // Increment attempt counter for each changed question
    changed.forEach((qId) => {
      attemptCountRef.current.set(qId, (attemptCountRef.current.get(qId) ?? 0) + 1);
    });

    // Cancel any pending debounce timer
    if (timerRef.current !== null) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setIsSaving(true);

      const draft: Array<{
        question_id: string;
        answer: AutosaveAnswerValue;
        idempotency_key: string;
      }> = [];

      answers.forEach((answer, questionId) => {
        const n = attemptCountRef.current.get(questionId) ?? 0;
        draft.push({
          question_id: questionId,
          answer,
          idempotency_key: makeIdempotencyKey(sessionId, questionId, n),
        });
      });

      if (typeof window !== 'undefined') {
        localStorage.setItem(`quiz-draft-${sessionId}`, JSON.stringify(draft));
      }

      prevAnswersRef.current = new Map(answers);
      setIsSaving(false);
      setLastSaved(new Date());
    }, delayMs);

    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, [sessionId, answers, delayMs]);

  return { isSaving, lastSaved };
}
