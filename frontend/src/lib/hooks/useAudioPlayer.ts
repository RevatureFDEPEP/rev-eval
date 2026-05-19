/**
 * useAudioPlayer Hook
 *
 * Manages audio playback using the Web Audio API.
 * Provides real-time volume monitoring for visual feedback (Orb animation).
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';

interface UseAudioPlayerReturn {
  isPlaying: boolean;
  isPaused: boolean;
  outputVolume: number; // 0-1 scale for visualization
  currentTime: number; // Current playback position in seconds
  duration: number; // Total duration in seconds
  progress: number; // Progress as percentage (0-100)
  play: (audioUrl: string) => Promise<void>;
  pause: () => void;
  resume: () => void;
  restart: () => void;
  stop: () => void;
  seek: (time: number) => void;
  onPlaybackEnd: (callback: () => void) => void;
  error: string | null;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [outputVolume, setOutputVolume] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const playbackEndCallbackRef = useRef<(() => void) | null>(null);

  /**
   * Set up audio analyzer for volume monitoring
   */
  const setupVolumeMonitoring = useCallback((audioElement: HTMLAudioElement) => {
    try {
      // Create audio context if it doesn't exist
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      const audioContext = audioContextRef.current;

      // Resume audio context if suspended
      if (audioContext.state === 'suspended') {
        audioContext.resume();
      }

      // Create analyzer
      if (!analyserRef.current) {
        analyserRef.current = audioContext.createAnalyser();
        analyserRef.current.fftSize = 256;
        analyserRef.current.smoothingTimeConstant = 0.3;
      }

      // Disconnect old source if it exists
      if (sourceRef.current) {
        try {
          sourceRef.current.disconnect();
        } catch (e) {
          // Ignore disconnect errors
        }
      }

      // Create new source for this audio element
      if (audioElement) {
        sourceRef.current = audioContext.createMediaElementSource(audioElement);
        sourceRef.current.connect(analyserRef.current);
        analyserRef.current.connect(audioContext.destination);
      }

      console.log('✅ Audio volume monitoring set up');
    } catch (err) {
      console.error('❌ Failed to set up audio volume monitoring:', err);
    }
  }, []);

  /**
   * Monitor audio output volume and playback progress
   */
  const monitorVolume = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateVolume = () => {
      analyser.getByteFrequencyData(dataArray);

      // Calculate average volume (0-255)
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;

      // Normalize to 0-1 range
      const normalized = Math.min(average / 128, 1);

      setOutputVolume(normalized);

      // Update playback progress
      if (audioRef.current) {
        const time = audioRef.current.currentTime;
        const dur = audioRef.current.duration;

        setCurrentTime(time);
        if (dur && !isNaN(dur)) {
          setDuration(dur);
          setProgress((time / dur) * 100);
        }
      }

      // Continue monitoring if playing
      if (audioRef.current && !audioRef.current.paused && !audioRef.current.ended) {
        animationFrameRef.current = requestAnimationFrame(updateVolume);
      } else {
        // Reset volume when not playing
        setOutputVolume(0);
      }
    };

    updateVolume();
  }, []);

  /**
   * Play audio from URL or Blob
   */
  const play = useCallback(async (audioUrl: string) => {
    try {
      console.log('🔊 Playing audio...');

      // Stop current playback if any
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }

      // Create new audio element with preload and CORS support
      const audio = new Audio(audioUrl);
      audio.preload = 'metadata'; // Preload metadata (duration, dimensions) before playing
      audio.crossOrigin = 'anonymous'; // Enable CORS for Web Audio API (volume monitoring)
      audioRef.current = audio;

      // Wait for metadata to load before playing
      const metadataLoaded = new Promise<void>((resolve) => {
        audio.onloadedmetadata = () => {
          setDuration(audio.duration);
          console.log('✅ Audio metadata loaded, duration:', audio.duration);
          resolve();
        };
      });

      audio.onplay = () => {
        setIsPlaying(true);
        setIsPaused(false);
        setError(null);
        console.log('✅ Audio playing');

        // Start volume monitoring
        monitorVolume();
      };

      audio.onpause = () => {
        setIsPlaying(false);
        setIsPaused(true);
        console.log('⏸️ Audio paused');
      };

      audio.onended = () => {
        setIsPlaying(false);
        setIsPaused(false);
        setOutputVolume(0);
        setCurrentTime(0);
        setProgress(0);
        console.log('✅ Audio playback ended');

        // Stop volume monitoring
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = null;
        }

        // Call playback end callback
        if (playbackEndCallbackRef.current) {
          playbackEndCallbackRef.current();
        }
      };

      audio.onerror = (e) => {
        console.error('❌ Audio playback error:', e);
        setIsPlaying(false);
        setIsPaused(false);
        setOutputVolume(0);
        setError('Failed to play audio');
        toast.error('Failed to play audio');
      };

      // Set up volume monitoring (must be done before play)
      setupVolumeMonitoring(audio);

      // Wait for metadata to load first
      await metadataLoaded;

      // Now play audio with duration already known
      await audio.play();
    } catch (err) {
      console.error('❌ Failed to play audio:', err);
      setError('Failed to play audio');
      toast.error('Failed to play audio');
      setIsPlaying(false);
    }
  }, [setupVolumeMonitoring, monitorVolume]);

  /**
   * Pause audio playback
   */
  const pause = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      console.log('⏸️ Audio paused');
    }
  }, []);

  /**
   * Resume audio playback
   */
  const resume = useCallback(() => {
    if (audioRef.current && audioRef.current.paused && !audioRef.current.ended) {
      audioRef.current.play().catch((err) => {
        console.error('❌ Failed to resume audio:', err);
        toast.error('Failed to resume audio');
      });
      console.log('▶️ Audio resumed');
    }
  }, []);

  /**
   * Restart audio from beginning
   */
  const restart = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      if (audioRef.current.paused) {
        audioRef.current.play().catch((err) => {
          console.error('❌ Failed to restart audio:', err);
          toast.error('Failed to restart audio');
        });
      }
      console.log('🔄 Audio restarted');
    }
  }, []);

  /**
   * Stop audio playback
   */
  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      setIsPaused(false);
      setOutputVolume(0);
      setCurrentTime(0);
      setProgress(0);

      // Stop volume monitoring
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }

      console.log('🛑 Audio stopped');
    }
  }, []);

  /**
   * Seek to specific time in audio
   */
  const seek = useCallback((time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, Math.min(time, audioRef.current.duration));
      console.log('⏩ Seeked to:', time);
    }
  }, []);

  /**
   * Set callback for when playback ends
   */
  const onPlaybackEnd = useCallback((callback: () => void) => {
    playbackEndCallbackRef.current = callback;
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      // Stop playback
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      // Close audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      // Cancel animation frame
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return {
    isPlaying,
    isPaused,
    outputVolume,
    currentTime,
    duration,
    progress,
    play,
    pause,
    resume,
    restart,
    stop,
    seek,
    onPlaybackEnd,
    error,
  };
}
