import { api } from "./api";

export interface SettingsResponse {
  embedding_model: string;
  embedding_dimension: number;
  chunk_size: number;
  chunk_overlap: number;
  qdrant_collection: string;
  llm_model: string;
  llm_temperature: number;
  max_retries: number;
  rate_limit_max_requests: number;
  rate_limit_window_seconds: number;
  ocr_language: string;
  deepseek_api_key_set: boolean;
  hybrid_search_enabled: boolean;
}

export interface SettingsUpdate {
  chunk_size?: number;
  chunk_overlap?: number;
  llm_temperature?: number;
  max_retries?: number;
  ocr_language?: string;
}

export async function getSettings(): Promise<SettingsResponse> {
  const { data } = await api.get<SettingsResponse>("/api/v1/settings");
  return data;
}

export async function updateSettings(body: SettingsUpdate): Promise<SettingsResponse> {
  const { data } = await api.put<SettingsResponse>("/api/v1/settings", body);
  return data;
}

export async function resetSettings(): Promise<void> {
  await api.post("/api/v1/settings/reset");
}

export async function getSettingsHealth(): Promise<Record<string, { status: string; version?: string; error?: string; model?: string }>> {
  const { data } = await api.get("/api/v1/settings/health");
  return data;
}
