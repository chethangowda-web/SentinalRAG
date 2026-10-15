import { api, clearStoredToken, getStoredToken } from "./api";
import type {
  ChatMessageList,
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionList,
  ChatStepEvent,
} from "@/types";

export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/v1/chat", request);
  return data;
}

/**
 * Ask a question and receive pipeline progress as it happens (Server-Sent Events).
 * Resolves with the final answer; `onStep` fires once per finished pipeline node.
 * If the stream cannot be opened at all (e.g. an older backend), falls back to the
 * regular request so the caller never has to care.
 */
export async function streamChatMessage(
  request: ChatRequest,
  onStep?: (step: ChatStepEvent) => void,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const token = getStoredToken();
  let response: Response;
  try {
    response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(request),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    return sendChatMessage(request);
  }

  if (response.status === 401) {
    clearStoredToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Not authenticated");
  }
  if (!response.ok || !response.body) {
    return sendChatMessage(request);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatResponse | null = null;

  const handleBlock = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (data.length === 0) return;
    const payload = JSON.parse(data.join("\n"));
    if (event === "step") onStep?.(payload as ChatStepEvent);
    else if (event === "result") result = payload as ChatResponse;
    else if (event === "error") throw new Error(payload.detail || "The pipeline failed");
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      handleBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
    }
  }
  if (buffer.trim()) handleBlock(buffer);

  if (!result) throw new Error("The connection closed before an answer was received");
  return result;
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
