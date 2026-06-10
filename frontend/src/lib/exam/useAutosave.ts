/**
 * useAutosave — debounced periodic autosave of in-progress answers (W3-F4 step 2).
 *
 * Whenever the answers change while `enabled`, a save is scheduled `intervalMs`
 * (default 30s) after the LATEST change (debounce — a flurry of edits collapses
 * to one PATCH). The save sends the full answer map to `PATCH /sessions/{id}/draft`
 * so a crash/close doesn't lose work. Disabled once the exam is locked/submitted.
 *
 * `saveFn` is injectable so unit tests run without the network.
 */
'use client';

import { useEffect, useRef, useState } from 'react';
import { saveDraft as defaultSaveDraft } from '@/lib/api/sessions';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

type SaveFn = (sessionId: string, answers: Record<string, number[]>) => Promise<unknown>;

const DEFAULT_INTERVAL_MS = 30_000;

export function useAutosave(
  sessionId: string,
  answers: Map<string, number[]>,
  enabled: boolean,
  intervalMs: number = DEFAULT_INTERVAL_MS,
  saveFn: SaveFn = defaultSaveDraft,
): SaveStatus {
  const [status, setStatus] = useState<SaveStatus>('idle');

  // Latest answers, read at fire-time so the debounced save sends current state.
  const answersRef = useRef(answers);
  answersRef.current = answers;

  // Change detection: a stable serialization of the answer entries.
  const serialized = JSON.stringify(Array.from(answers.entries()));
  const lastSavedRef = useRef<string>('');

  useEffect(() => {
    if (!enabled) return;
    if (answers.size === 0) return;
    if (serialized === lastSavedRef.current) return;

    const handle = setTimeout(async () => {
      setStatus('saving');
      const payload = Object.fromEntries(answersRef.current.entries());
      try {
        await saveFn(sessionId, payload);
        lastSavedRef.current = JSON.stringify(
          Array.from(answersRef.current.entries()),
        );
        setStatus('saved');
      } catch {
        setStatus('error');
      }
    }, intervalMs);

    return () => clearTimeout(handle);
    // `serialized` re-arms the debounce on every answer change.
  }, [serialized, enabled, intervalMs, sessionId, saveFn, answers.size]);

  return status;
}
