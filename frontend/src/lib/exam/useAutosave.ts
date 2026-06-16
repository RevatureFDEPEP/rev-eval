/**
 * useAutosave — debounced periodic autosave of in-progress answers (W3-F4 step 2).
 *
 * Whenever the answers change while `enabled`, a save is scheduled `intervalMs`
 * (default 30s) after the LATEST change (debounce — a flurry of edits collapses
 * to one PATCH), **capped** so the save fires no later than `intervalMs` after
 * the FIRST unsaved change — a candidate answering more often than the interval
 * still persists a draft every interval. The save sends the full answer map to
 * `PATCH /sessions/{id}/draft` so a crash/close doesn't lose work. Disabled once
 * the exam is locked/submitted.
 *
 * A semantic 409/410 from the save means the session is terminal
 * (submitted/expired): autosaving HALTS permanently — surface and halt, never
 * keep PATCHing a finished exam. Other failures keep the existing behavior of
 * retrying on the next answer change.
 *
 * `saveFn` is injectable so unit tests run without the network.
 */
'use client';

import { useEffect, useRef, useState } from 'react';
import { ApiError } from '@/lib/api/client';
import { saveDraft as defaultSaveDraft } from '@/lib/api/sessions';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

type SaveFn = (sessionId: string, answers: Record<string, number[]>) => Promise<unknown>;

const DEFAULT_INTERVAL_MS = 30_000;

// Server decisions that make the session terminal — stop autosaving.
const TERMINAL_STATUSES = new Set([409, 410]);

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
  useEffect(() => {
    answersRef.current = answers;
  });

  // Change detection: a stable serialization of the answer entries.
  const serialized = JSON.stringify(Array.from(answers.entries()));
  const lastSavedRef = useRef<string>('');
  // Wall-clock of the first change since the last save — the max-wait floor.
  const dirtySinceRef = useRef<number | null>(null);
  // Latched on a semantic 409/410: the session is terminal, never PATCH again.
  const haltedRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    if (haltedRef.current) return;
    if (answers.size === 0) return;
    if (serialized === lastSavedRef.current) return;

    if (dirtySinceRef.current === null) {
      dirtySinceRef.current = Date.now();
    }
    // Trailing debounce (intervalMs after this change) capped by the max-wait
    // (intervalMs after the first unsaved change).
    const maxWaitRemaining = dirtySinceRef.current + intervalMs - Date.now();
    const delay = Math.max(0, Math.min(intervalMs, maxWaitRemaining));

    const handle = setTimeout(async () => {
      setStatus('saving');
      const payload = Object.fromEntries(answersRef.current.entries());
      try {
        await saveFn(sessionId, payload);
        lastSavedRef.current = JSON.stringify(
          Array.from(answersRef.current.entries()),
        );
        dirtySinceRef.current = null;
        setStatus('saved');
      } catch (err) {
        if (err instanceof ApiError && TERMINAL_STATUSES.has(err.status)) {
          haltedRef.current = true;
        }
        dirtySinceRef.current = null; // next change starts a fresh window
        setStatus('error');
      }
    }, delay);

    return () => clearTimeout(handle);
    // `serialized` re-arms the debounce on every answer change.
  }, [serialized, enabled, intervalMs, sessionId, saveFn, answers.size]);

  return status;
}
