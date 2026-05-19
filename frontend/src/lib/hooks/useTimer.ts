/**
 * useTimer Hook
 *
 * Countdown timer with localStorage persistence and auto-submit functionality.
 * Provides warnings at 5 minutes and 1 minute remaining.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

const WARNING_5_MIN_SECONDS = 5 * 60; // 5 minutes in seconds
const WARNING_1_MIN_SECONDS = 1 * 60; // 1 minute in seconds

interface UseTimerOptions {
  durationSeconds: number;  // Total duration in seconds
  testId: string;           // Test ID for localStorage key
  onTimeExpired: () => void; // Callback when time runs out
  autoStart?: boolean;      // Auto-start timer on mount (default: true)
}

interface UseTimerReturn {
  timeRemaining: number;    // Seconds remaining
  formatTime: () => string; // Formatted MM:SS string
  isWarning: boolean;       // True if < 5 minutes remaining
  isCritical: boolean;      // True if < 1 minute remaining
  isExpired: boolean;       // True if time is up
  pause: () => void;        // Pause the timer
  resume: () => void;       // Resume the timer
  reset: (overrideDuration?: number) => void;        // Reset to initial (or provided) duration
}

export function useTimer(options: UseTimerOptions): UseTimerReturn {
  const {
    durationSeconds,
    testId,
    onTimeExpired,
    autoStart = true,
  } = options;

  const STORAGE_KEY = `quiz-timer-${testId}`;

  // Load initial time from localStorage or use duration
  const getInitialTime = (): number => {
    if (typeof window === 'undefined') return durationSeconds;

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const { timeRemaining, timestamp } = JSON.parse(stored);
      const now = Date.now();
      const elapsedSeconds = Math.floor((now - timestamp) / 1000);
      const remaining = Math.max(0, timeRemaining - elapsedSeconds);
      return remaining;
    }
    return durationSeconds;
  };

  const [timeRemaining, setTimeRemaining] = useState<number>(getInitialTime);
  const [isRunning, setIsRunning] = useState<boolean>(autoStart);
  const [isExpired, setIsExpired] = useState<boolean>(false);

  const warning5MinShown = useRef<boolean>(false);
  const warning1MinShown = useRef<boolean>(false);
  const expiredCallbackFired = useRef<boolean>(false);

  // Save time to localStorage
  const saveToLocalStorage = useCallback((remaining: number) => {
    if (typeof window === 'undefined') return;

    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      timeRemaining: remaining,
      timestamp: Date.now(),
    }));
  }, [STORAGE_KEY]);

  // Clear localStorage
  const clearLocalStorage = useCallback(() => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(STORAGE_KEY);
  }, [STORAGE_KEY]);

  // Show warning toasts
  useEffect(() => {
    if (timeRemaining <= WARNING_1_MIN_SECONDS && !warning1MinShown.current && timeRemaining > 0) {
      warning1MinShown.current = true;
      toast.warning('1 Minute Remaining!', {
        description: 'Test will auto-submit when time expires.',
        duration: 5000,
      });
    } else if (timeRemaining <= WARNING_5_MIN_SECONDS && !warning5MinShown.current && timeRemaining > 0) {
      warning5MinShown.current = true;
      toast.warning('5 Minutes Remaining', {
        description: 'Please review your answers.',
        duration: 5000,
      });
    }
  }, [timeRemaining]);

  // Timer countdown
  useEffect(() => {
    if (!isRunning || timeRemaining <= 0) return;

    const intervalId = setInterval(() => {
      setTimeRemaining((prev) => {
        const newTime = Math.max(0, prev - 1);
        saveToLocalStorage(newTime);

        if (newTime === 0) {
          setIsExpired(true);
          setIsRunning(false);
          clearLocalStorage();

          // Fire expired callback only once
          if (!expiredCallbackFired.current) {
            expiredCallbackFired.current = true;
            setTimeout(() => onTimeExpired(), 100);
          }
        }

        return newTime;
      });
    }, 1000);

    return () => clearInterval(intervalId);
  }, [isRunning, timeRemaining, onTimeExpired, saveToLocalStorage, clearLocalStorage]);

  // Format time as MM:SS
  const formatTime = useCallback((): string => {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }, [timeRemaining]);

  // Pause timer
  const pause = useCallback(() => {
    setIsRunning(false);
    saveToLocalStorage(timeRemaining);
  }, [timeRemaining, saveToLocalStorage]);

  // Resume timer
  const resume = useCallback(() => {
    if (!isExpired && timeRemaining > 0) {
      setIsRunning(true);
    }
  }, [isExpired, timeRemaining]);

  // Reset timer
  const reset = useCallback((overrideDuration?: number) => {
    const nextDuration = typeof overrideDuration === 'number' ? overrideDuration : durationSeconds;

    setTimeRemaining(nextDuration);
    setIsRunning(autoStart && nextDuration > 0);
    setIsExpired(false);
    warning5MinShown.current = false;
    warning1MinShown.current = false;
    expiredCallbackFired.current = false;
    saveToLocalStorage(nextDuration);
  }, [durationSeconds, autoStart, saveToLocalStorage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeRemaining > 0) {
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
