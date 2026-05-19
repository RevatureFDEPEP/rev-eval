/**
 * useInterviewWebSocket Hook
 *
 * Manages WebSocket connection to the AI Interview Service backend.
 * Handles connection lifecycle, message sending/receiving, and auto-reconnection.
 *
 * Backend WebSocket endpoint: ws://localhost:8009/ws/{session_id}?submission_id={submission_id}
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

export interface InterviewMessage {
  mime_type: 'text/plain';
  data: string;
  role: 'user' | 'assistant' | 'system';
  error?: boolean;
  interview_ended?: boolean;
}

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseInterviewWebSocketOptions {
  onInterviewEnd?: () => void;
  onError?: (error: string) => void;
  autoReconnect?: boolean;
}

interface UseInterviewWebSocketReturn {
  connectionState: ConnectionState;
  messages: InterviewMessage[];
  sendMessage: (text: string) => void;
  isInterviewEnded: boolean;
  sessionId: string | null;
  connect: (sessionId: string, submissionId: number) => void;
  disconnect: () => void;
  clearMessages: () => void;
}

export function useInterviewWebSocket(
  options: UseInterviewWebSocketOptions = {}
): UseInterviewWebSocketReturn {
  const { onInterviewEnd, onError, autoReconnect = true } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [messages, setMessages] = useState<InterviewMessage[]>([]);
  const [isInterviewEnded, setIsInterviewEnded] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const submissionIdRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const completionToastShownRef = useRef(false); // Track if completion toast has been shown
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(function connectInternal(sessionId: string, submissionId: number) {
    // Store connection params for reconnection
    sessionIdRef.current = sessionId;
    submissionIdRef.current = submissionId;

    // Get WebSocket URL from environment
    const wsBaseUrl = process.env.NEXT_PUBLIC_INTERVIEW_WS_URL || 'ws://localhost:8009';
    const wsUrl = `${wsBaseUrl}/ws/${sessionId}?submission_id=${submissionId}`;

    console.log('🔌 Connecting to WebSocket:', wsUrl);
    setConnectionState('connecting');

    try {
      const ws = new WebSocket(wsUrl);

      // Connection opened
      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setConnectionState('connected');
        reconnectAttemptsRef.current = 0;
        completionToastShownRef.current = false; // Reset toast flag for new connection
      };

      // Message received
      ws.onmessage = (event) => {
        try {
          const message: InterviewMessage = JSON.parse(event.data);
          console.log('📨 Received message:', message);

          // Add message to state
          setMessages((prev) => [...prev, message]);

          // Handle interview end - only show toast once
          if (message.interview_ended && !completionToastShownRef.current) {
            console.log('🏁 Interview ended');
            setIsInterviewEnded(true);
            completionToastShownRef.current = true; // Mark toast as shown
            toast.success('Interview completed');
            onInterviewEnd?.();
          } else if (message.interview_ended && completionToastShownRef.current) {
            // Message already processed, just update state without showing toast
            console.log('🏁 Interview ended (already processed)');
            setIsInterviewEnded(true);
          }

          // Handle errors
          if (message.error) {
            console.error('❌ Server error:', message.data);
            toast.error(message.data);
            onError?.(message.data);
          }
        } catch (error) {
          console.error('❌ Failed to parse message:', error);
        }
      };

      // Connection closed
      ws.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        setConnectionState('disconnected');

        // Attempt reconnection if not intentional close and not ended
        if (autoReconnect && event.code !== 1000 && !isInterviewEnded) {
          if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttemptsRef.current++;
            console.log(
              `🔄 Reconnecting... (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`
            );
            toast.info('Connection lost. Reconnecting...');

            reconnectTimeoutRef.current = setTimeout(() => {
              if (sessionIdRef.current && submissionIdRef.current) {
                connectInternal(sessionIdRef.current, submissionIdRef.current);
              }
            }, RECONNECT_DELAY);
          } else {
            console.error('❌ Max reconnection attempts reached');
            toast.error('Unable to reconnect. Please refresh the page.');
            setConnectionState('error');
          }
        }
      };

      // Connection error
      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setConnectionState('error');
        toast.error('Connection error occurred');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error);
      setConnectionState('error');
      toast.error('Failed to connect to interview service');
    }
  }, [autoReconnect, isInterviewEnded, onInterviewEnd, onError]);

  /**
   * Send message to WebSocket
   */
  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      toast.error('Cannot send message: not connected');
      return;
    }

    const message: InterviewMessage = {
      mime_type: 'text/plain',
      data: text,
      role: 'user',
    };

    try {
      wsRef.current.send(JSON.stringify(message));
      console.log('📤 Sent message:', message);

      // Add user message to local state immediately
      setMessages((prev) => [...prev, message]);
    } catch (error) {
      console.error('❌ Failed to send message:', error);
      toast.error('Failed to send message');
    }
  }, []);

  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting WebSocket...');

    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setConnectionState('disconnected');
  }, []);

  /**
   * Clear messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    messages,
    sendMessage,
    isInterviewEnded,
    sessionId: sessionIdRef.current,
    connect,
    disconnect,
    clearMessages,
  };
}
