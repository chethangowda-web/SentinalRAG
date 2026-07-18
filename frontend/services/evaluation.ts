import { api } from "./api";
import type { EvaluationResult, EvaluationHistoryItem } from "@/types";

export async function runEvaluation(): Promise<EvaluationResult> {
  const { data } = await api.post<EvaluationResult>("/api/v1/evaluate");
  return data;
}

export async function getEvaluationReport(): Promise<EvaluationResult> {
  const { data } = await api.get<EvaluationResult>("/api/v1/evaluation/report");
  return data;
}

export async function getEvaluationHistory(): Promise<EvaluationHistoryItem[]> {
  const { data } = await api.get<EvaluationHistoryItem[]>("/api/v1/evaluation/history");
  return data;
}
