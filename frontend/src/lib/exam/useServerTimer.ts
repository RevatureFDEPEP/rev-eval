/**
 * useServerTimer — a live countdown anchored to SERVER time (W3-F4 spec step 1).
 *
 * The remaining seconds are computed from the session's `server_now`/`expires_at`
 * (the W3-F1 contract), never the client clock, to absorb client clock skew:
 *
 *   baseline   = expires_at − server_now            (captured once at mount)
 *   remaining  = baseline − (Date.now() − mountWall) (elapsed wall time since mount)
 *
 * A 1s interval re-derives `remaining` from elapsed wall-clock (not by decrementing
 * a counter, so a throttled/background tab can't drift). At zero it fires `onExpire`
 * exactly once (auto-submit) and clamps at 0.
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

  useEffect(() => {
    if (!enabled) return;

    // Anchor wall-clock at mount/enable; remaining is re-derived from elapsed
    // wall time so a throttled/background tab cannot drift.
    const mountWall = Date.now();
    let fired = false;

    const tick = () => {
      const elapsed = Math.floor((Date.now() - mountWall) / 1000);
      const remaining = Math.max(0, baseline - elapsed);
      setTimeRemaining(remaining);
      if (remaining === 0 && !fired) {
        fired = true;
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
