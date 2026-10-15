import { api } from "./api";
import type { EvaluationResult, EvaluationHistoryItem, DocumentEvaluation, DocumentEvaluationDetail, DocumentComparison, EvaluationDashboard } from "@/types";

export interface EvalTaskResponse {
  evaluation_id: string;
  status: "running";
  total_questions: number;
}

export interface EvalStatusResponse {
  evaluation_id: string;
  status: "running" | "completed" | "failed";
  progress: number;
  total: number;
  error: string | null;
}

export interface BenchmarkStatus {
  ready: boolean;
  loading: boolean;
  documents: { filename: string; status: string }[];
}

export interface EvaluationLatest {
  report: EvaluationResult | null;
  run: EvalStatusResponse | null;
  benchmark: BenchmarkStatus;
}

/** Last report, any run in flight, and benchmark readiness in one call (never 404s). */
export async function getEvaluationLatest(): Promise<EvaluationLatest> {
  const { data } = await api.get<EvaluationLatest>("/api/v1/evaluation/latest");
  return data;
}

export async function setupBenchmark(): Promise<BenchmarkStatus> {
  const { data } = await api.post<BenchmarkStatus>("/api/v1/evaluation/benchmark/setup");
  return data;
}

export async function runEvaluation(): Promise<EvalTaskResponse> {
  const { data } = await api.post<EvalTaskResponse>("/api/v1/evaluate");
  return data;
}

export async function getEvaluationStatus(evaluationId: string): Promise<EvalStatusResponse> {
  const { data } = await api.get<EvalStatusResponse>(`/api/v1/evaluation/status/${evaluationId}`);
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

export async function getDocumentEvaluations(): Promise<DocumentEvaluation[]> {
  const { data } = await api.get<DocumentEvaluation[]>("/api/v1/evaluations/documents");
  return data;
}

export async function getDocumentEvaluation(documentId: string): Promise<DocumentEvaluationDetail> {
  const { data } = await api.get<DocumentEvaluationDetail>(`/api/v1/evaluations/documents/${documentId}`);
  return data;
}

export async function compareDocumentEvaluations(doc1: string, doc2: string): Promise<DocumentComparison> {
  const { data } = await api.get<DocumentComparison>(`/api/v1/evaluations/documents/compare/${doc1}/${doc2}`);
  return data;
}

export async function getEvaluationDashboard(): Promise<EvaluationDashboard> {
  const { data } = await api.get<EvaluationDashboard>("/api/v1/evaluations/dashboard");
  return data;
}
