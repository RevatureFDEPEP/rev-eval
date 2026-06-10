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
  // Captured once at mount — recomputing would defeat the skew-absorbing anchor.
  const mountWallRef = useRef<number>(Date.now());
  const baselineRef = useRef<number>(
    Math.max(
      0,
      Math.floor(
        (new Date(expiresAt).getTime() - new Date(serverNow).getTime()) / 1000,
      ),
    ),
  );
  const [timeRemaining, setTimeRemaining] = useState<number>(baselineRef.current);
  const firedRef = useRef(false);

  // Keep the latest onExpire without resetting the interval each render.
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      const elapsed = Math.floor((Date.now() - mountWallRef.current) / 1000);
      const remaining = Math.max(0, baselineRef.current - elapsed);
      setTimeRemaining(remaining);
      if (remaining === 0 && !firedRef.current) {
        firedRef.current = true;
        onExpireRef.current();
      }
    };

    tick(); // sync immediately so the first paint shows the real value
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [enabled]);

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
