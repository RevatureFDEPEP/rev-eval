/**
 * Server-anchored countdown timer (W3-F4, spec step 1).
 *
 * Anchored to the server's own clock:
 *   baseline   = expires_at − server_now           (seconds the server granted)
 *   remaining  = baseline − (now_wall − mount_wall) (elapsed since mount)
 * so the client's absolute clock skew never matters — only elapsed wall time
 * does. Each tick re-derives `remaining` from the wall clock rather than
 * decrementing a counter, so a throttled/backgrounded tab can't drift.
 *
 * `onExpire` fires exactly once when the clock reaches zero. The timer stops
 * when `enabled` is false (e.g. the session is locked after submit).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export interface ServerTimer {
  timeRemaining: number; // whole seconds, clamped at 0
  formatTime: () => string; // "m:ss"
  isWarning: boolean; // < 5 minutes
  isCritical: boolean; // < 1 minute
}

const WARNING_SECONDS = 300;
const CRITICAL_SECONDS = 60;

export function useServerTimer(
  serverNow: string,
  expiresAt: string,
  onExpire: () => void,
  enabled = true
): ServerTimer {
  // Baseline is pure (derived from server timestamps) — safe to compute in render.
  const baseline = useMemo(
    () =>
      (new Date(expiresAt).getTime() - new Date(serverNow).getTime()) / 1000,
    [expiresAt, serverNow]
  );

  // Seed with the full granted time; the first tick (≈mount) corrects for elapsed.
  const [timeRemaining, setTimeRemaining] = useState(() =>
    Math.max(0, Math.round(baseline))
  );

  // Wall-clock anchor captured once at mount (impure → effect, not render).
  const mountWallRef = useRef<number | null>(null);
  useEffect(() => {
    mountWallRef.current = Date.now() / 1000;
  }, []);

  // Keep the latest onExpire without restarting the interval each render.
  const onExpireRef = useRef(onExpire);
  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);
  const firedRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    // Reset the one-shot per activation. If the timer is re-enabled while still
    // past expiry (e.g. a submit advanced the session because the server hadn't
    // expired yet), onExpire must fire again to keep driving toward the lock —
    // otherwise the countdown freezes at 0:00 and stops enforcing time.
    firedRef.current = false;
    const tick = () => {
      const mountWall = mountWallRef.current ?? Date.now() / 1000;
      const elapsed = Date.now() / 1000 - mountWall;
      const remaining = Math.max(0, Math.round(baseline - elapsed));
      setTimeRemaining(remaining);
      if (remaining <= 0 && !firedRef.current) {
        firedRef.current = true;
        onExpireRef.current();
      }
    };
    tick(); // sync immediately, don't wait a full second
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [enabled, baseline]);

  const formatTime = useCallback(() => {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, [timeRemaining]);

  return {
    timeRemaining,
    formatTime,
    isWarning: timeRemaining < WARNING_SECONDS,
    isCritical: timeRemaining < CRITICAL_SECONDS,
  };
}
