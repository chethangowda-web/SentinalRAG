import { api } from "./api";
import type { HealthResponse } from "@/types";

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/api/v1/health");
  return data;
}
