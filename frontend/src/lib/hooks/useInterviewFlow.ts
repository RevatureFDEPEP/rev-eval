/**
 * useInterviewFlow Hook
 *
 * Orchestrates the complete interview flow by coordinating:
 * - WebSocket communication
 * - Audio recording and playback
 * - State transitions
 * - Text-to-speech and speech-to-text conversions
 *
 * This is the main hook that manages the interview lifecycle.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { useInterviewWebSocket, type InterviewMessage, type ConnectionState } from './useInterviewWebSocket';
import { useAudioRecorder } from './useAudioRecorder';
import { useAudioPlayer } from './useAudioPlayer';
import { uploadInterviewAudio } from '../api/interview';

export type InterviewState =
  | 'initializing'    // Loading test, creating session
  | 'connecting'      // Establishing WebSocket
  | 'ready'           // Connected, showing instructions
  | 'ai-speaking'     // Playing AI question audio
  | 'user-speaking'   // Recording user response
  | 'processing'      // Transcribing + sending to backend
  | 'waiting'         // Waiting for AI response
  | 'completed'       // Interview ended
  | 'error';          // Fatal error

interface UseInterviewFlowOptions {
  submissionId: number;
  onComplete?: () => void;
}

interface UseInterviewFlowReturn {
  interviewState: InterviewState;
  messages: InterviewMessage[];
  connectionState: ConnectionState;
  inputVolume: number;
  outputVolume: number;
  isRecording: boolean;
  hasPermission: boolean;
  isMuted: boolean;
  startInterview: () => Promise<void>;
  stopSpeaking: () => Promise<void>;
  endInterview: () => Promise<void>;
  toggleMute: () => void;
  error: string | null;
}

export function useInterviewFlow(options: UseInterviewFlowOptions): UseInterviewFlowReturn {
  const { submissionId, onComplete } = options;

  const [interviewState, setInterviewState] = useState<InterviewState>('initializing');
  const [error, setError] = useState<string | null>(null);
  const isProcessingRef = useRef(false);
  const latestMessageRef = useRef<InterviewMessage | null>(null);
  const hasEverConnectedRef = useRef(false);
  const interviewEndProcessedRef = useRef(false); // Track if interview end has been processed
  const sessionIdRef = useRef<string | null>(null); // Track session ID for audio uploads
  const messageIndexRef = useRef<number>(0); // Track message index for audio uploads

  // Initialize sub-hooks
  const websocket = useInterviewWebSocket({
    onInterviewEnd: () => {
      // Don't do anything here - the useEffect will handle it
      // This prevents duplicate state updates
      console.log('🏁 Interview ended callback (handled by useEffect)');
    },
    onError: (err) => {
      console.error('❌ WebSocket error:', err);
      setError(err);
      setInterviewState('error');
    },
    autoReconnect: true,
  });

  const audioRecorder = useAudioRecorder();
  const audioPlayer = useAudioPlayer();

  /**
   * Start the interview
   */
  const startInterview = useCallback(async () => {
    try {
      console.log('🎬 Starting interview...');
      setInterviewState('connecting');
      setError(null);
      hasEverConnectedRef.current = false;
      interviewEndProcessedRef.current = false; // Reset interview end processing flag

      // Request microphone permission first and ensure stream is active
      if (!audioRecorder.hasPermission) {
        console.log('🎤 Requesting microphone permission...');
        await audioRecorder.requestPermission();
        console.log('✅ Microphone permission granted');
      }

      // Generate unique session ID
      const sessionId = `interview-${submissionId}-${Date.now()}`;
      console.log('🔑 Session ID:', sessionId);

      // Store session ID for audio uploads
      sessionIdRef.current = sessionId;
      messageIndexRef.current = 0; // Reset message index

      // Connect to WebSocket - state will be updated via useEffect when connected
      console.log('🔌 Initiating WebSocket connection...');
      websocket.connect(sessionId, submissionId);
    } catch (err) {
      console.error('❌ Failed to start interview:', err);
      setError(err instanceof Error ? err.message : 'Failed to start interview');
      setInterviewState('error');
      toast.error('Failed to start interview');
    }
  }, [submissionId, audioRecorder, websocket]);

  /**
   * Handle AI response (text → speech → play)
   */
  /**
   * Stop speaking and process user response
   */
  const stopSpeaking = useCallback(async () => {
    if (!audioRecorder.isRecording) {
      console.warn('⚠️ Not currently recording');
      return;
    }

    try {
      console.log('🛑 Stopping recording and processing...');
      setInterviewState('processing');

      // Stop recording and get audio blob
      const audioBlob = await audioRecorder.stopRecording();

      if (!audioBlob) {
        throw new Error('No audio recorded');
      }

      console.log('🎙️ Audio blob size:', audioBlob.size, 'bytes');

      // Upload user response audio to S3 (non-blocking, but capture index immediately)
      const audioUploadPromise = (async () => {
        if (sessionIdRef.current !== null) {
          const currentIndex = messageIndexRef.current;
          messageIndexRef.current++; // Increment IMMEDIATELY to avoid race conditions
          console.log(`📤 Uploading user audio for message ${currentIndex}...`);
          try {
            const audioUrl = await uploadInterviewAudio(sessionIdRef.current, currentIndex, audioBlob);
            console.log(`✅ User audio uploaded: ${audioUrl}`);
          } catch (err) {
            console.error(`❌ Failed to upload user audio for message ${currentIndex}:`, err);
            // Don't block interview flow on upload failure
          }
        }
      })();

      // Convert speech to text via BFF
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch('/api/elevenlabs/speech-to-text', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to transcribe audio');
      }

      const { text } = await response.json();
      console.log('📝 Transcribed text:', text);

      if (!text || text.trim().length === 0) {
        throw new Error('No speech detected');
      }

      // Send transcript to backend via WebSocket
      websocket.sendMessage(text);

      // Set state to waiting (AI is thinking) - this will show in the orb
      setInterviewState('waiting');
    } catch (err) {
      console.error('❌ Failed to process user response:', err);
      setError('Failed to process response');
      toast.error(err instanceof Error ? err.message : 'Failed to process response');

      // Go back to user speaking so they can try again
      setInterviewState('user-speaking');
    }
  }, [audioRecorder, websocket]);

  /**
   * Handle AI response (text → speech → play)
   * @param text - The AI response text
   * @param isFinalMessage - If true, don't auto-start recording after playback
   * @returns Promise that resolves when audio playback completes
   */
  const handleAIResponse = useCallback(async (text: string, isFinalMessage: boolean = false): Promise<void> => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;

    return new Promise<void>((resolve) => {
      (async () => {
        try {
          console.log('🤖 Processing AI response:', text.substring(0, 50) + '...');
          setInterviewState('ai-speaking');

          // Convert text to speech via BFF
          const response = await fetch('/api/elevenlabs/text-to-speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
          });

          if (!response.ok) {
            throw new Error('Failed to convert text to speech');
          }

          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);

          // Upload AI question audio to S3 (non-blocking, but capture index immediately)
          const audioUploadPromise = (async () => {
            if (sessionIdRef.current !== null) {
              const currentIndex = messageIndexRef.current;
              messageIndexRef.current++; // Increment IMMEDIATELY to avoid race conditions
              console.log(`📤 Uploading AI audio for message ${currentIndex}...`);
              try {
                const s3Url = await uploadInterviewAudio(sessionIdRef.current, currentIndex, audioBlob);
                console.log(`✅ AI audio uploaded: ${s3Url}`);
              } catch (err) {
                console.error(`❌ Failed to upload AI audio for message ${currentIndex}:`, err);
                // Don't block interview flow on upload failure
              }
            }
          })();

          // Set up playback end callback before playing
          audioPlayer.onPlaybackEnd(() => {
            console.log('🎵 Audio playback completed');
            
            if (isFinalMessage) {
              // Final message - don't start recording, just resolve
              console.log('🏁 Final message audio completed');
              resolve();
            } else {
              // Regular message - start recording for next user response
              setInterviewState('user-speaking');
              audioRecorder.startRecording();
              resolve();
            }
          });

          // Play audio
          await audioPlayer.play(audioUrl);
        } catch (err) {
          console.error('❌ Failed to process AI response:', err);
          setError('Failed to play AI response');
          toast.error('Failed to play audio. Switching to text-only mode.');

          if (isFinalMessage) {
            // For final message, resolve anyway so interview can end
            resolve();
          } else {
            // Fallback: skip audio and go straight to user recording
            setInterviewState('user-speaking');
            audioRecorder.startRecording();
            resolve();
          }
        } finally {
          isProcessingRef.current = false;
        }
      })();
    });
  }, [audioPlayer, audioRecorder, stopSpeaking]);

  /**
   * End the interview gracefully
   */
  const endInterview = useCallback(async () => {
    try {
      console.log('🏁 Ending interview...');

      // Stop recording if active
      if (audioRecorder.isRecording) {
        await audioRecorder.stopRecording();
      }

      // Stop audio playback if active
      if (audioPlayer.isPlaying) {
        audioPlayer.stop();
      }

      // Call backend API to end interview session
      const sessionId = websocket.sessionId;
      if (sessionId) {
        try {
          const wsBaseUrl = process.env.NEXT_PUBLIC_INTERVIEW_WS_URL || 'ws://localhost:8009';
          const httpBaseUrl = wsBaseUrl.replace('ws://', 'http://').replace('wss://', 'https://');
          const endUrl = `${httpBaseUrl}/sessions/${sessionId}/end`;
          
          console.log('📞 Calling backend to end interview:', endUrl);
          const response = await fetch(endUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            console.error('❌ Failed to end interview on backend:', errorData);
            toast.error('Failed to end interview on server');
          } else {
            console.log('✅ Interview ended successfully on backend');
          }
        } catch (fetchErr) {
          console.error('❌ Error calling end interview endpoint:', fetchErr);
          toast.error('Failed to communicate with server');
        }
      }

      // Disconnect WebSocket
      websocket.disconnect();

      setInterviewState('completed');
      onComplete?.();
    } catch (err) {
      console.error('❌ Failed to end interview:', err);
      toast.error('Failed to end interview properly');
    }
  }, [audioRecorder, audioPlayer, websocket, onComplete]);

  /**
   * Watch for new messages and handle AI responses
   */
  useEffect(() => {
    const latestMessage = websocket.messages[websocket.messages.length - 1];

    console.log('📩 Messages changed, latest:', latestMessage?.role, 'total:', websocket.messages.length);

    // Skip if no new message or already processing
    if (!latestMessage || latestMessage === latestMessageRef.current) {
      console.log('⏭️ Skipping - no new message or already processed');
      return;
    }

    latestMessageRef.current = latestMessage;
    console.log('📨 Processing new message:', latestMessage);

    // Handle interview end - but wait for final audio to play if it's an assistant message
    // Only process once to avoid duplicate notifications and multiple /end calls
    if (latestMessage.interview_ended && !interviewEndProcessedRef.current) {
      console.log('🏁 Interview ended via WebSocket');
      interviewEndProcessedRef.current = true; // Mark as processed
      
      // Call backend to end interview and update submission status
      const callEndInterview = async () => {
        const sessionId = websocket.sessionId;
        if (sessionId) {
          try {
            const wsBaseUrl = process.env.NEXT_PUBLIC_INTERVIEW_WS_URL || 'ws://localhost:8009';
            const httpBaseUrl = wsBaseUrl.replace('ws://', 'http://').replace('wss://', 'https://');
            const endUrl = `${httpBaseUrl}/sessions/${sessionId}/end`;
            
            console.log('📞 Calling backend to end interview and update submission:', endUrl);
            const response = await fetch(endUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
            });

            if (!response.ok) {
              const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
              console.error('❌ Failed to end interview on backend:', errorData);
              // Don't show error to user - interview is already functionally ended
            } else {
              console.log('✅ Interview ended successfully on backend, submission updated');
            }
          } catch (fetchErr) {
            console.error('❌ Error calling end interview endpoint:', fetchErr);
            // Don't show error to user - interview is already functionally ended
          }
        }
      };
      
      // IMPORTANT: Call /end endpoint IMMEDIATELY to save evaluations before WebSocket disconnects
      // The WebSocket cleanup will disconnect and remove the session from memory,
      // so we need to call /end while the session and agent are still available
      console.log('📞 Calling /end endpoint immediately to save evaluations...');
      
      // Call /end endpoint and wait for it to complete before proceeding
      const endInterviewPromise = callEndInterview().then(() => {
        console.log('✅ /end endpoint completed successfully');
      }).catch((err) => {
        console.error('❌ Failed to call /end endpoint:', err);
        // Continue anyway - we'll try to play the final message
      });

      // If this is an assistant message with interview_ended, play it after /end completes
      if (latestMessage.role === 'assistant' && latestMessage.data) {
        console.log('🎵 Waiting for /end to complete, then playing final message...');
        endInterviewPromise.then(() => {
          // After /end completes, play the final message audio
          handleAIResponse(latestMessage.data, true).then(() => {
            console.log('✅ Final message audio completed');
            // Don't disconnect WebSocket yet - let it stay connected until user navigates away
            setInterviewState('completed');
            onComplete?.();
          }).catch((err) => {
            console.error('❌ Error playing final message:', err);
            // Still end the interview even if audio fails
            setInterviewState('completed');
            onComplete?.();
          });
        });
      } else {
        // System message or no data - wait for /end then end immediately
        endInterviewPromise.then(() => {
          setInterviewState('completed');
          onComplete?.();
        });
      }
      return;
    }

    // Handle errors
    if (latestMessage.error) {
      console.error('❌ Server error:', latestMessage.data);
      setError(latestMessage.data);
      toast.error('Server error: ' + latestMessage.data);
      return;
    }

    // Handle AI assistant messages
    if (latestMessage.role === 'assistant' && interviewState !== 'ai-speaking') {
      console.log('💬 New AI message received, calling handleAIResponse');
      handleAIResponse(latestMessage.data);
    } else {
      console.log('⏭️ Skipping message - role:', latestMessage.role, 'state:', interviewState);
    }
  }, [websocket.messages, interviewState, handleAIResponse, onComplete]);

  /**
   * Sync interview state with connection state
   */
  useEffect(() => {
    console.log('🔄 Connection state changed:', websocket.connectionState, 'Interview state:', interviewState);

    if (websocket.connectionState === 'connected') {
      hasEverConnectedRef.current = true;
      if (interviewState === 'connecting' || interviewState === 'error') {
        console.log('✅ WebSocket connected, transitioning to ready');
        setInterviewState('ready');
        setError(null);
      }
      return;
    }

    if (websocket.connectionState === 'error') {
      console.error('❌ WebSocket error detected');
      setInterviewState('error');
      setError('Connection failed');
      return;
    }

    if (
      websocket.connectionState === 'disconnected' &&
      hasEverConnectedRef.current &&
      !websocket.isInterviewEnded &&
      interviewState !== 'completed'
    ) {
      console.error('❌ WebSocket disconnected unexpectedly');
      setInterviewState('error');
      setError('Connection lost');
    }
  }, [websocket.connectionState, websocket.isInterviewEnded, interviewState]);

  // Auto-stop timer removed - user controls when to stop speaking

  return {
    interviewState,
    messages: websocket.messages,
    connectionState: websocket.connectionState,
    inputVolume: audioRecorder.inputVolume,
    outputVolume: audioPlayer.outputVolume,
    isRecording: audioRecorder.isRecording,
    hasPermission: audioRecorder.hasPermission,
    isMuted: audioRecorder.isMuted,
    startInterview,
    stopSpeaking,
    endInterview,
    toggleMute: audioRecorder.toggleMute,
    error: error || audioRecorder.error || audioPlayer.error,
  };
}
