from datetime import datetime

from pydantic import BaseModel


class GraphExecutionRecord(BaseModel):
    node_name: str
    execution_time_ms: float = 0.0
    input: str | None = None
    output: str | None = None
    decision: str | None = None
    next_node: str | None = None
    retry_count: int = 0


class RetrievalDetail(BaseModel):
    chunk_id: str = ""
    document_id: str = ""
    text: str = ""
    vector_score: float = 0.0
    bm25_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    final_rank: int = 0
    selected: bool = False
    reason: str = ""


class ConfidenceBreakdown(BaseModel):
    vector_similarity: float = 0.0
    vector_contribution: float = 0.0
    coverage: float = 0.0
    coverage_contribution: float = 0.0
    cross_encoder_score: float = 0.0
    cross_encoder_contribution: float = 0.0
    citation_count: int = 0
    contradiction_status: str = "none"
    retry_success: bool = False
    citation_contribution: float = 0.0
    raw_score: float = 0.0
    final_score: float = 0.0


class LLMObservability(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model_name: str = ""
    temperature: float = 0.0
    retries: int = 0
    failures: int = 0


class TraceResponse(BaseModel):
    id: str
    timestamp: datetime | str
    original_query: str
    rewritten_query: str | None = None
    confidence_before_rewrite: float = 0.0
    confidence_after_rewrite: float | None = None
    retrieval_attempts: int = 1
    reason_for_retry: str | None = None
    contradiction_detected: bool = False
    contradiction_reason: str | None = None
    clarification_needed: bool = False
    clarification_question: str | None = None
    final_confidence: float = 0.0
    final_confidence_level: str = "LOW"
    execution_path: list[str] = []
    graph_execution: list[dict] = []
    retrieval_details: list[dict] = []
    confidence_breakdown: dict | None = None
    llm_observability: dict | None = None
    session_timeline: str | None = None
    answer: str | None = None
    citations: list[dict] = []
    latencies: dict[str, float] = {}
