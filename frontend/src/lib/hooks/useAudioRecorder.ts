/**
 * useAudioRecorder Hook
 *
 * Manages browser microphone access and audio recording using MediaRecorder.
 * Provides lightweight volume monitoring for UI feedback and optional
 * silence-based auto stop.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';

const IS_DEV = process.env.NODE_ENV !== 'production';
const SILENCE_THRESHOLD = 0.0125;

interface UseAudioRecorderReturn {
  isRecording: boolean;
  hasPermission: boolean;
  inputVolume: number;
  isMuted: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  requestPermission: () => Promise<void>;
  toggleMute: () => void;
  error: string | null;
}

const SUPPORTED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
] as const;

function getSupportedMimeType(): string {
  if (typeof MediaRecorder === 'undefined') {
    return 'audio/webm';
  }

  for (const type of SUPPORTED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return 'audio/webm';
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [inputVolume, setInputVolume] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const recordingStartedAtRef = useRef<number>(0);
  const requestDataIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const teardownStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const setupVolumeMonitoring = useCallback(async (stream: MediaStream) => {
    try {
      const AudioContextCtor =
        typeof window !== 'undefined'
          ? window.AudioContext ||
            (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
          : undefined;

      if (!AudioContextCtor) {
        console.error('❌ AudioContext is not supported in this browser');
        return;
      }

      const audioContext = new AudioContextCtor();

      // CRITICAL: Resume AudioContext if suspended (Chrome/Safari requirement)
      if (audioContext.state === 'suspended') {
        console.log('⚠️ AudioContext is suspended, attempting to resume...');
        await audioContext.resume();
        console.log('✅ AudioContext resumed. State:', audioContext.state);
      } else {
        console.log('✅ AudioContext state:', audioContext.state);
      }

      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);

      const gainNode = audioContext.createGain();
      gainNode.gain.value = 25;

      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.3;

      microphone.connect(gainNode);
      gainNode.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      if (IS_DEV) {
        console.log('✅ Volume monitor initialised (gain boost x25)');
        console.log('🎙️ AudioContext sampleRate:', audioContext.sampleRate);
        console.log('🎙️ AnalyserNode frequencyBinCount:', analyser.frequencyBinCount);
      }
    } catch (err) {
      console.error('❌ Failed to set up volume monitoring:', err);
    }
  }, []);

  const monitorVolume = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateVolume = () => {
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
      const normalized = Math.min(average / 255, 1);

      setInputVolume(normalized);

      if (IS_DEV && Date.now() % 200 < 30) {
        console.log('🎤 Volume monitor', {
          raw: average.toFixed(2),
          normalized: normalized.toFixed(3),
          threshold: SILENCE_THRESHOLD,
        });
      }

      // Continue monitoring
      animationFrameRef.current = requestAnimationFrame(updateVolume);
    };

    animationFrameRef.current = requestAnimationFrame(updateVolume);
  }, []);

  const requestPermission = useCallback(async () => {
    try {
      if (!streamRef.current) {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 44100,
            channelCount: 1,
          },
        });
        streamRef.current = stream;
        await setupVolumeMonitoring(stream);
      }

      setHasPermission(true);
      setError(null);
    } catch (err) {
      console.error('❌ Microphone permission denied:', err);
      setHasPermission(false);
      setError('Microphone access denied');
      toast.error('Please allow microphone access to continue');
    }
  }, [setupVolumeMonitoring]);

  const startRecording = useCallback(
    async () => {
      try {
        // Always ensure we have a fresh, active stream
        if (!hasPermission || !streamRef.current) {
          await requestPermission();
        }

        // Check if stream exists and has active tracks
        if (!streamRef.current) {
          throw new Error('No media stream available');
        }

        // Verify stream has active audio tracks - recreate if needed
        const audioTracks = streamRef.current.getAudioTracks();
        const hasActiveTracks = audioTracks.length > 0 && audioTracks.some(track => track.readyState === 'live' && track.enabled);
        
        if (!hasActiveTracks) {
          console.log('⚠️ Stream tracks are not active, recreating stream...');
          // Stop old stream
          teardownStream();
          // Request new stream
          await requestPermission();
          
          if (!streamRef.current) {
            throw new Error('Failed to create media stream');
          }
        }

        // Reset tracking refs (keeping for potential future use, but not using for auto-stop)
        recordingStartedAtRef.current = Date.now();

        const stream = streamRef.current;
        const mimeType = getSupportedMimeType();

        // Verify stream has active audio tracks
        const finalAudioTracks = stream.getAudioTracks();
        if (finalAudioTracks.length === 0) {
          throw new Error('No audio tracks in stream');
        }

        console.log('🎙️ Audio tracks:', finalAudioTracks.length);
        finalAudioTracks.forEach((track, idx) => {
          console.log(`  Track ${idx}:`, {
            id: track.id,
            label: track.label,
            enabled: track.enabled,
            muted: track.muted,
            readyState: track.readyState,
            settings: track.getSettings(),
          });
          
          // Ensure track is enabled
          if (!track.enabled) {
            track.enabled = true;
            console.log(`  ✅ Enabled track ${idx}`);
          }
        });

        // Verify MediaRecorder support for mimeType
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          console.warn(`⚠️ ${mimeType} not supported, trying fallback`);
        }

        // Ensure all tracks are enabled before creating MediaRecorder
        finalAudioTracks.forEach(track => {
          if (!track.enabled) {
            track.enabled = true;
          }
        });

        const mediaRecorder = new MediaRecorder(stream, { mimeType });
        audioChunksRef.current = [];

        mediaRecorder.onstart = () => {
          console.log('✅ MediaRecorder.onstart fired - recording has begun');
        };

        mediaRecorder.ondataavailable = (event) => {
          console.log('📦 ondataavailable fired:', {
            size: event.data.size,
            type: event.data.type,
            timecode: event.timecode,
          });

          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
            console.log('✅ Chunk stored. Total chunks:', audioChunksRef.current.length);
          } else {
            console.error('❌ EMPTY CHUNK - size is 0!');
          }
        };

        mediaRecorder.onerror = (event) => {
          console.error('❌ MediaRecorder.onerror:', event);
          setError('Recording error');
        };

        mediaRecorder.onpause = () => {
          console.log('⏸️ MediaRecorder paused');
        };

        mediaRecorder.onresume = () => {
          console.log('▶️ MediaRecorder resumed');
        };

        mediaRecorderRef.current = mediaRecorder;

        console.log('🎙️ About to call mediaRecorder.start(100)');
        console.log('🎙️ Current state:', mediaRecorder.state); // Should be 'inactive'

        try {
          // Start without timeslice - we'll manually request data
          mediaRecorder.start();
          console.log('✅ mediaRecorder.start() called');
          console.log('🎙️ New state:', mediaRecorder.state); // Should be 'recording'

          // Manually request data every 100ms for better browser compatibility
          // Some browsers don't respect the timeslice parameter properly
          requestDataIntervalRef.current = setInterval(() => {
            if (mediaRecorder.state === 'recording') {
              try {
                mediaRecorder.requestData();
                console.log('🔄 Manually requested data chunk');
              } catch (err) {
                console.error('❌ requestData() failed:', err);
              }
            }
          }, 100);

          console.log('🔄 Set up manual data request interval (every 100ms)');
        } catch (err) {
          console.error('❌ Failed to call start():', err);
          throw err;
        }

        setIsRecording(true);
        setError(null);

        if (IS_DEV) {
          console.log('🎙️ MediaRecorder setup complete:', {
            mimeType,
            state: mediaRecorder.state,
            videoBitsPerSecond: mediaRecorder.videoBitsPerSecond,
            audioBitsPerSecond: mediaRecorder.audioBitsPerSecond,
          });
        }

        monitorVolume();
      } catch (err) {
        console.error('❌ Failed to start recording:', err);
        setError('Failed to start recording');
        toast.error('Failed to start recording');
      }
    },
    [hasPermission, requestPermission, monitorVolume, teardownStream]
  );

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const mediaRecorder = mediaRecorderRef.current;
      if (!mediaRecorder || mediaRecorder.state !== 'recording') {
        resolve(null);
        return;
      }

      mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || getSupportedMimeType();
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

        setIsRecording(false);
        setInputVolume(0);

        // Clear manual data request interval
        if (requestDataIntervalRef.current) {
          clearInterval(requestDataIntervalRef.current);
          requestDataIntervalRef.current = null;
          console.log('🛑 Cleared manual data request interval');
        }

        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = null;
        }

        if (IS_DEV) {
          console.log('🛑 Recording stopped. Size:', audioBlob.size);
          console.log('🛑 Total chunks collected:', audioChunksRef.current.length);
        }

        resolve(audioBlob.size > 0 ? audioBlob : null);
      };

      try {
        mediaRecorder.requestData();
      } catch (err) {
        if (IS_DEV) {
          console.warn('⚠️ requestData failed:', err);
        }
      }

      mediaRecorder.stop();
    });
  }, []);

  // Cleanup when recording state changes
  useEffect(() => {
    return () => {
      if (isRecording && mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }

      // Clear manual data request interval
      if (requestDataIntervalRef.current) {
        clearInterval(requestDataIntervalRef.current);
        requestDataIntervalRef.current = null;
      }

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }

      // Note: We don't teardown the stream here to keep it alive for the next recording
      // The stream will be cleaned up when the component unmounts
    };
  }, [isRecording]);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      teardownStream();
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
    };
  }, [teardownStream]);

  const toggleMute = useCallback(() => {
    if (streamRef.current) {
      const audioTracks = streamRef.current.getAudioTracks();
      if (audioTracks.length > 0) {
        const newMutedState = !isMuted;
        audioTracks.forEach((track) => {
          track.enabled = !newMutedState;
        });
        setIsMuted(newMutedState);
        console.log(newMutedState ? '🔇 Microphone muted (recording silence)' : '🎤 Microphone unmuted');
      }
    }
  }, [isMuted]);

  return {
    isRecording,
    hasPermission,
    inputVolume,
    isMuted,
    startRecording,
    stopRecording,
    requestPermission,
    toggleMute,
    error,
  };
}
