import { api } from "./api";
import type { ChatRequest, ChatResponse } from "@/types";

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/v1/chat", request);
  return data;
}
