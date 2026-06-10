/**
 * useServerTimer — a live countdown anchored to SERVER time (W3-F4 spec step 1).
 *
 * The remaining seconds are computed from the session's `server_now`/`expires_at`
 * (the W3-F1 contract), never the client clock, to absorb client clock skew:
 *
 *   baseline   = expires_at − server_now                  (captured once at mount)
 *   deadline   = Date.now() + baseline*1000               (anchored ONCE, first enable)
 *   remaining  = (deadline − Date.now()) / 1000           (re-derived every tick)
 *
 * The deadline is stored in a ref on the FIRST enabled run and never moves —
 * `enabled` toggles (every submit cycles active → submitting → active) must not
 * re-anchor the countdown against the original full baseline (W3-F7 item 1).
 *
 * A 1s interval re-derives `remaining` from the absolute deadline (not by
 * decrementing a counter, so a throttled/background tab can't drift). At zero it
 * fires `onExpire` exactly once (auto-submit) and clamps at 0.
 */
'use client';

import { useEffect, useRef, useState } from 'react';

export interface ServerTimerState {
  timeRemaining: number; // seconds, clamped at 0
  formatTime: () => string; // "M:SS"
  isWarning: boolean; // < 5 minutes
  isCritical: boolean; // < 1 minute
}

const WARNING_THRESHOLD = 300; // 5 min
const CRITICAL_THRESHOLD = 60; // 1 min

export function useServerTimer(
  serverNow: string,
  expiresAt: string,
  onExpire: () => void,
  enabled = true,
): ServerTimerState {
  // Pure: parse the server timestamps to a starting remaining-seconds value
  // (no Date.now here — the wall-clock anchor is captured in the effect below).
  const baseline = Math.max(
    0,
    Math.floor(
      (new Date(expiresAt).getTime() - new Date(serverNow).getTime()) / 1000,
    ),
  );
  const [timeRemaining, setTimeRemaining] = useState<number>(baseline);

  // Keep the latest onExpire without resetting the interval each render.
  const onExpireRef = useRef(onExpire);
  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  // Absolute deadline (client clock), anchored once; survives enabled toggles.
  const deadlineRef = useRef<number | null>(null);
  // onExpire single-fire across re-enables, not per effect run.
  const firedRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    if (deadlineRef.current === null) {
      deadlineRef.current = Date.now() + baseline * 1000;
    }
    const deadline = deadlineRef.current;

    const tick = () => {
      // ceil: remaining rounds UP so the first paint shows the full baseline
      // even when the tick lands a few ms after the anchor was captured
      // (floor read 59:59 on slow CI), and 0 is reached only at the true
      // deadline — matching the old baseline−floor(elapsed) semantics.
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setTimeRemaining(remaining);
      if (remaining === 0 && !firedRef.current) {
        firedRef.current = true;
        onExpireRef.current();
      }
    };

    tick(); // sync immediately so the first paint shows the real value
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [enabled, baseline]);

  const formatTime = () => {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return {
    timeRemaining,
    formatTime,
    isWarning: timeRemaining < WARNING_THRESHOLD,
    isCritical: timeRemaining < CRITICAL_THRESHOLD,
  };
}
