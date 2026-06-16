'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

const WARNING_5_MIN_SECONDS = 5 * 60;
const WARNING_1_MIN_SECONDS = 1 * 60;

interface UseTimerOptions {
  durationSeconds: number;
  /**
   * Server-anchored deadline (epoch ms).
   * When provided the timer computes remaining time from this absolute deadline
   * on every tick — accurate after page reload regardless of localStorage state.
   * Computed as: Date.parse(session.started_at) + duration_seconds * 1000
   */
  expiresAtMs?: number;
  testId: string;
  onTimeExpired: () => void;
  autoStart?: boolean;
}

interface UseTimerReturn {
  timeRemaining: number;
  formatTime: () => string;
  isWarning: boolean;
  isCritical: boolean;
  isExpired: boolean;
  pause: () => void;
  resume: () => void;
  /** Pass overrideExpiresAtMs to switch to server-anchored mode (or update the deadline). */
  reset: (overrideDuration?: number, overrideExpiresAtMs?: number) => void;
}

export function useTimer(options: UseTimerOptions): UseTimerReturn {
  const {
    durationSeconds,
    expiresAtMs,
    testId,
    onTimeExpired,
    autoStart = true,
  } = options;

  const STORAGE_KEY = `quiz-timer-${testId}`;

  // Mutable ref for the active deadline — updated by reset().
  const currentExpiresAtMsRef = useRef<number | undefined>(expiresAtMs);

  // Sync ref when the option changes (e.g. on re-render after session creation)
  useEffect(() => {
    currentExpiresAtMsRef.current = expiresAtMs;
  }, [expiresAtMs]);

  const getInitialTime = (): number => {
    // Server-anchored: compute from absolute deadline using the option value (not ref)
    // The ref is only for use inside effects/handlers; options are safe to read during init.
    if (expiresAtMs !== undefined) {
      return Math.max(0, Math.round((expiresAtMs - Date.now()) / 1000));
    }

    if (typeof window === 'undefined') return durationSeconds;

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const { timeRemaining, timestamp } = JSON.parse(stored) as {
          timeRemaining: number;
          timestamp: number;
        };
        const elapsedSeconds = Math.floor((Date.now() - timestamp) / 1000);
        return Math.max(0, timeRemaining - elapsedSeconds);
      } catch {
        // corrupted — fall through to duration
      }
    }
    return durationSeconds;
  };

  const [timeRemaining, setTimeRemaining] = useState<number>(getInitialTime);
  const [isRunning, setIsRunning] = useState<boolean>(autoStart);
  const [isExpired, setIsExpired] = useState<boolean>(false);

  const warning5MinShown = useRef<boolean>(false);
  const warning1MinShown = useRef<boolean>(false);
  const expiredCallbackFired = useRef<boolean>(false);

  const saveToLocalStorage = useCallback(
    (remaining: number) => {
      if (typeof window === 'undefined') return;
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ timeRemaining: remaining, timestamp: Date.now() })
      );
    },
    [STORAGE_KEY]
  );

  const clearLocalStorage = useCallback(() => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(STORAGE_KEY);
  }, [STORAGE_KEY]);

  // Warning toasts
  useEffect(() => {
    if (timeRemaining <= WARNING_1_MIN_SECONDS && !warning1MinShown.current && timeRemaining > 0) {
      warning1MinShown.current = true;
      toast.warning('1 Minute Remaining!', {
        description: 'Test will auto-submit when time expires.',
        duration: 5000,
      });
    } else if (
      timeRemaining <= WARNING_5_MIN_SECONDS &&
      !warning5MinShown.current &&
      timeRemaining > 0
    ) {
      warning5MinShown.current = true;
      toast.warning('5 Minutes Remaining', {
        description: 'Please review your answers.',
        duration: 5000,
      });
    }
  }, [timeRemaining]);

  // Countdown interval
  useEffect(() => {
    if (!isRunning || timeRemaining <= 0) return;

    const intervalId = setInterval(() => {
      let newTime: number;

      if (currentExpiresAtMsRef.current !== undefined) {
        // Server-anchored: recompute from absolute deadline each tick
        newTime = Math.max(0, Math.round((currentExpiresAtMsRef.current - Date.now()) / 1000));
      } else {
        // Local countdown: decrement and persist
        newTime = Math.max(0, timeRemaining - 1);
        saveToLocalStorage(newTime);
      }

      setTimeRemaining(newTime);

      if (newTime === 0 && !expiredCallbackFired.current) {
        expiredCallbackFired.current = true;
        setIsExpired(true);
        setIsRunning(false);
        clearLocalStorage();
        setTimeout(() => onTimeExpired(), 100);
      }
    }, 1000);

    return () => clearInterval(intervalId);
  }, [isRunning, timeRemaining, onTimeExpired, saveToLocalStorage, clearLocalStorage]);

  const formatTime = useCallback((): string => {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }, [timeRemaining]);

  const pause = useCallback(() => {
    setIsRunning(false);
    if (currentExpiresAtMsRef.current === undefined) {
      saveToLocalStorage(timeRemaining);
    }
  }, [timeRemaining, saveToLocalStorage]);

  const resume = useCallback(() => {
    if (!isExpired && timeRemaining > 0) {
      setIsRunning(true);
    }
  }, [isExpired, timeRemaining]);

  const reset = useCallback(
    (overrideDuration?: number, overrideExpiresAtMs?: number) => {
      // Update the deadline ref
      if (overrideExpiresAtMs !== undefined) {
        currentExpiresAtMsRef.current = overrideExpiresAtMs;
      } else if (overrideDuration !== undefined) {
        currentExpiresAtMsRef.current = undefined;
      }

      // Compute starting time
      let initial: number;
      if (currentExpiresAtMsRef.current !== undefined) {
        initial = Math.max(0, Math.round((currentExpiresAtMsRef.current - Date.now()) / 1000));
      } else {
        initial = typeof overrideDuration === 'number' ? overrideDuration : durationSeconds;
      }

      setTimeRemaining(initial);
      setIsRunning(autoStart && initial > 0);
      setIsExpired(false);
      warning5MinShown.current = false;
      warning1MinShown.current = false;
      expiredCallbackFired.current = false;

      if (currentExpiresAtMsRef.current === undefined) {
        saveToLocalStorage(initial);
      }
    },
    [durationSeconds, autoStart, saveToLocalStorage]
  );

  // Persist on unmount (local mode only)
  useEffect(() => {
    return () => {
      if (timeRemaining > 0 && currentExpiresAtMsRef.current === undefined) {
        saveToLocalStorage(timeRemaining);
      }
    };
  }, [timeRemaining, saveToLocalStorage]);

  return {
    timeRemaining,
    formatTime,
    isWarning: timeRemaining <= WARNING_5_MIN_SECONDS && timeRemaining > 0,
    isCritical: timeRemaining <= WARNING_1_MIN_SECONDS && timeRemaining > 0,
    isExpired,
    pause,
    resume,
    reset,
  };
}
