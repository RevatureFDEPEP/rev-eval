/**
 * Debounced draft autosave with a max-wait cap (W3-F4, spec step 2).
 *
 * Trailing 30s debounce: each *content* change to the answers map (re)arms the
 * timer, so a save fires 30s after the last change. Keying on a serialized
 * snapshot (not the Map reference) means a keystroke that re-selects the same
 * options won't churn the timer. A `maxWaitMs` cap bounds staleness so
 * a *continuously* interacting participant (who would otherwise keep resetting
 * the debounce and never save) still flushes at least every `maxWaitMs` — the
 * pending save is scheduled for `min(debounce, maxWait − sinceLastSave)`.
 *
 * The pending save is cancelled on unmount and never scheduled while `enabled`
 * is false (e.g. the session is locked after submit). Autosave is a *confirmed*
 * update — the status only reads "saved" after the server acks.
 */

import { useEffect, useRef, useState } from 'react';
import { saveDraft } from '@/lib/api/sessions';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

const DEBOUNCE_MS = 30_000;

/**
 * Canonical, order-independent serialization of the answer map, used purely as
 * the effect's change key. Sorting keys and each selection array means two maps
 * with identical content (regardless of insertion / click order) compare equal,
 * so a keystroke that doesn't change the answers won't re-arm the debounce.
 */
function serializeAnswers(answers: Map<string, number[]>): string {
  return JSON.stringify(
    [...answers.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => [k, [...v].sort((x, y) => x - y)])
  );
}

export function useAutosave(
  sessionId: string,
  answers: Map<string, number[]>,
  enabled = true,
  debounceMs = DEBOUNCE_MS,
  maxWaitMs = DEBOUNCE_MS
): SaveStatus {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');

  // Wall-clock of the last save start, used for the max-wait cap. Seeded at
  // mount so the first change waits a full debounce window, not 0.
  const lastSaveRef = useRef(0);
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    lastSaveRef.current = Date.now();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Keep the latest map in a ref so the timer always saves current answers
  // while the effect re-arms only on actual content change (serialized below).
  const answersRef = useRef(answers);
  useEffect(() => {
    answersRef.current = answers;
  });
  const serialized = serializeAnswers(answers);

  useEffect(() => {
    if (!enabled) return;
    // Cap the wait so sustained interaction can't starve the save forever.
    const sinceLastSave = Date.now() - lastSaveRef.current;
    const wait = Math.max(0, Math.min(debounceMs, maxWaitMs - sinceLastSave));
    const id = setTimeout(async () => {
      lastSaveRef.current = Date.now();
      if (mountedRef.current) setSaveStatus('saving');
      try {
        await saveDraft(sessionId, Object.fromEntries(answersRef.current));
        if (mountedRef.current) setSaveStatus('saved');
      } catch {
        if (mountedRef.current) setSaveStatus('error');
      }
    }, wait);
    return () => clearTimeout(id);
  }, [serialized, enabled, sessionId, debounceMs, maxWaitMs]);

  return saveStatus;
}
