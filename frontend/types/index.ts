export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds?: number;
}

export interface ChatRequest {
  question: string;
}

export interface CitationItem {
  document_id: string;
  chunk_id: string;
  page: number | null;
  text: string | null;
}

export interface ChatResponse {
  answer: string;
  confidence: number;
  confidence_level: "HIGH" | "MEDIUM" | "LOW";
  reasoning_path: string[];
  citations: CitationItem[];
  clarification_question: string | null;
  latencies: Record<string, number> | null;
  trace_id: string | null;
}

export interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  text: string;
  page: number | null;
  section: string | null;
  filename: string | null;
  vector_score: number;
  bm25_score: number;
  rerank_score: number;
}

export interface SearchResponse {
  query: string;
  confidence: number;
  confidence_level: "HIGH" | "MEDIUM" | "LOW";
  results: SearchResultItem[];
  latencies: Record<string, number> | null;
}

export interface SearchRequest {
  query: string;
}

export interface IngestResponse {
  document_id: string;
  status: string;
  pages: number;
  words: number;
  ocr_used: boolean;
  processing_time: number;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  pages: number | null;
  word_count: number | null;
  char_count: number | null;
  ocr_used: boolean;
  created_at: string;
  updated_at: string;
  file_size: number | null;
}

export interface ChunkMetadata {
  id: string;
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  char_start: number;
  char_end: number;
  word_count: number | null;
  page_number: number | null;
  embedding_status: string;
}

export interface ChunkListResponse {
  document_id: string;
  total_chunks: number;
  chunks: ChunkMetadata[];
}

export interface EvaluationSummary {
  baseline: Record<string, MetricValue>;
  sentinel: Record<string, MetricValue>;
  comparison: Record<string, ComparisonValue>;
}

export interface MetricValue {
  value: number;
  success: boolean;
  error: string | null;
  details: Record<string, unknown>;
}

export interface ComparisonValue {
  baseline: number;
  sentinel: number;
  absolute_change: number;
  relative_change_pct: number;
  direction: "up" | "down";
  improved: boolean;
}

export interface PerQuestionResult {
  id: string;
  question: string;
  ground_truth: string;
  category: string;
  has_contradiction: boolean;
  needs_clarification: boolean;
  has_context: boolean;
  baseline: PipelineResult;
  sentinel: PipelineResult;
}

export interface PipelineResult {
  answer: string;
  confidence_score: number;
  confidence_level: string;
  latencies: Record<string, number>;
  citations: CitationItem[];
  reasoning_path: string[];
  contradiction_detected: boolean;
  contradiction_reason: string | null;
  clarification_needed: boolean;
  clarification_question: string | null;
  retry_count: number;
}

export interface EvaluationResult {
  evaluation_id: string;
  timestamp: string;
  dataset: string;
  total_questions: number;
  summary: EvaluationSummary;
  per_question: PerQuestionResult[];
  failure_modes: Record<string, number>;
  reports?: Record<string, string>;
  visualizations?: string[];
}

export interface EvaluationHistoryItem {
  evaluation_id: string;
  timestamp: string;
  total_questions: number;
  dataset: string;
}

export interface EmbedResponse {
  document_id: string;
  total_chunks: number;
  embedded_chunks: number;
  status: string;
}

export interface GraphExecutionRecord {
  node_name: string;
  execution_time_ms: number;
  input: string | null;
  output: string | null;
  decision: string | null;
  next_node: string | null;
  retry_count: number;
}

export interface RetrievalDetail {
  chunk_id: string;
  document_id: string;
  text: string;
  vector_score: number;
  bm25_score: number;
  fusion_score: number;
  rerank_score: number;
  final_rank: number;
  selected: boolean;
  reason: string;
}

export interface ConfidenceBreakdown {
  vector_similarity: number;
  vector_contribution: number;
  coverage: number;
  coverage_contribution: number;
  cross_encoder_score: number;
  cross_encoder_contribution: number;
  citation_count: number;
  citation_contribution: number;
  contradiction_status: string;
  retry_success: boolean;
  raw_score: number;
  final_score: number;
}

export interface Trace {
  id: string;
  timestamp: string;
  original_query: string;
  rewritten_query: string | null;
  confidence_before_rewrite: number;
  confidence_after_rewrite: number | null;
  retrieval_attempts: number;
  reason_for_retry: string | null;
  contradiction_detected: boolean;
  contradiction_reason: string | null;
  clarification_needed: boolean;
  clarification_question: string | null;
  final_confidence: number;
  final_confidence_level?: ConfidenceLevel;
  execution_path: string[];
  graph_execution: GraphExecutionRecord[];
  retrieval_details: RetrievalDetail[];
  confidence_breakdown: ConfidenceBreakdown | null;
  llm_observability: Record<string, unknown> | null;
  session_timeline: string | null;
  answer: string | null;
  citations: CitationItem[];
  latencies: Record<string, number>;
  reasoning_path?: string[];
}

export interface TraceListResponse {
  total: number;
  skip: number;
  limit: number;
  traces: Trace[];
}

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";
