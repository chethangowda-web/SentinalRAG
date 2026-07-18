"use client";

import { useMutation } from "@tanstack/react-query";
import { sendChatMessage } from "@/services/chat";
import type { ChatRequest, ChatResponse } from "@/types";

export function useChat() {
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: sendChatMessage,
  });
}
