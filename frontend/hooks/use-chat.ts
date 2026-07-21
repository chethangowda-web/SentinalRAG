"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import {
  sendChatMessage,
  listSessions,
  createSession,
  updateSession,
  deleteSession,
  getSessionMessages,
  clearSessionMessages,
} from "@/services/chat";
import type {
  ChatMessageItem,
  ChatRequest,
  ChatResponse,
} from "@/types";

export function useChat() {
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: sendChatMessage,
  });
}

export function useChatSessions(params?: { search?: string }) {
  return useQuery({
    queryKey: ["chat-sessions", params?.search],
    queryFn: () => listSessions({ search: params?.search }),
  });
}

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => getSessionMessages(sessionId!),
    enabled: !!sessionId,
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) => createSession(title),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useUpdateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      ...body
    }: { sessionId: string; title?: string; pinned?: boolean }) =>
      updateSession(sessionId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => deleteSession(sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
  });
}

export function useClearSessionMessages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => clearSessionMessages(sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-session"] });
    },
  });
}

export function useChatSessionMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-session-messages", sessionId],
    queryFn: async () => {
      const result = await getSessionMessages(sessionId!);
      return result.messages;
    },
    enabled: !!sessionId,
  });
}

export function useStreamingChat() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingError, setStreamingError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (
      question: string,
      sessionId?: string | null
    ): Promise<ChatResponse> => {
      setIsStreaming(true);
      setStreamingError(null);
      abortRef.current = new AbortController();

      try {
        const response = await sendChatMessage({
          question,
          session_id: sessionId,
        });
        return response;
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Failed to send message";
        setStreamingError(msg);
        throw err;
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    []
  );

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }, []);

  return { sendMessage, isStreaming, streamingError, cancel };
}
