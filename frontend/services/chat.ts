import { api } from "./api";
import type {
  ChatMessageList,
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionList,
} from "@/types";

export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/v1/chat", request);
  return data;
}

export async function listSessions(
  params?: { skip?: number; limit?: number; search?: string }
): Promise<ChatSessionList> {
  const { data } = await api.get<ChatSessionList>("/api/v1/chat/history/sessions", { params });
  return data;
}

export async function createSession(
  title: string
): Promise<ChatSession> {
  const { data } = await api.post<ChatSession>("/api/v1/chat/history/sessions", { title });
  return data;
}

export async function updateSession(
  sessionId: string,
  body: { title?: string; pinned?: boolean }
): Promise<ChatSession> {
  const { data } = await api.patch<ChatSession>(
    `/api/v1/chat/history/sessions/${sessionId}`,
    body
  );
  return data;
}

export async function deleteSession(
  sessionId: string
): Promise<void> {
  await api.delete(`/api/v1/chat/history/sessions/${sessionId}`);
}

export async function getSessionMessages(
  sessionId: string,
  params?: { skip?: number; limit?: number }
): Promise<ChatMessageList> {
  const { data } = await api.get<ChatMessageList>(
    `/api/v1/chat/history/sessions/${sessionId}/messages`,
    { params }
  );
  return data;
}

export async function clearSessionMessages(
  sessionId: string
): Promise<void> {
  await api.delete(`/api/v1/chat/history/sessions/${sessionId}/messages`);
}
