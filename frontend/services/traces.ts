import { api } from "./api";
import type { Trace, TraceListResponse } from "@/types";

export async function fetchTraces(skip = 0, limit = 50): Promise<TraceListResponse> {
  const { data } = await api.get<TraceListResponse>("/api/v1/traces", {
    params: { skip, limit },
  });
  return data;
}

export async function fetchTrace(traceId: string): Promise<Trace> {
  const { data } = await api.get<Trace>(`/api/v1/traces/${traceId}`);
  return data;
}

export function getExportUrl(format: "json" | "csv" | "markdown"): string {
  const base = `${api.defaults.baseURL}/api/v1/traces/export`;
  return `${base}/${format}`;
}
