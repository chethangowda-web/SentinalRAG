from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


class CitationItem(BaseModel):
    document_id: str
    chunk_id: str
    page: int | None = None
    text: str | None = None


class GraphExecutionStep(BaseModel):
    node_name: str
    execution_time_ms: float
    input: str | None = None
    output: str | None = None
    decision: str | None = None
    next_node: str | None = None
    retry_count: int = 0


class RetrievalDetailItem(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    vector_score: float = 0
    bm25_score: float = 0
    fusion_score: float = 0
    rerank_score: float = 0
    final_rank: int = 0
    selected: bool = False
    reason: str = ""


class ConfidenceBreakdown(BaseModel):
    vector_similarity: float = 0
    vector_contribution: float = 0
    coverage: float = 0
    coverage_contribution: float = 0
    cross_encoder_score: float = 0
    cross_encoder_contribution: float = 0
    citation_count: int = 0
    citation_contribution: float = 0
    contradiction_status: str = "none"
    retry_success: bool = False
    raw_score: float = 0
    final_score: float = 0


class LLMObservability(BaseModel):
    rewrite_prompt_tokens: int = 0
    rewrite_completion_tokens: int = 0
    rewrite_total_tokens: int = 0
    rewrite_latency_ms: float = 0
    generation_prompt_tokens: int = 0
    generation_completion_tokens: int = 0
    generation_total_tokens: int = 0
    generation_latency_ms: float = 0
    model_name: str = ""
    temperature: float = 0


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    confidence_level: str
    reasoning_path: list[str]
    citations: list[CitationItem]
    clarification_question: str | None = None
    clarification_needed: bool = False
    latencies: dict[str, float] | None = None
    trace_id: str | None = None
    session_id: str | None = None
    graph_execution: list[GraphExecutionStep] = []
    retrieval_details: list[RetrievalDetailItem] = []
    confidence_breakdown: ConfidenceBreakdown | None = None
    llm_observability: LLMObservability | None = None
    rewritten_question: str | None = None
    retry_count: int = 0
    contradiction_detected: bool = False
    contradiction_reason: str | None = None
    model_used: str | None = None


### Chat History Models ###


class ChatSessionCreate(BaseModel):
    title: str = "New Chat"


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    response: ChatResponse | None = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    id: str
    title: str
    pinned: bool = False
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None
    last_confidence_level: str | None = None


class ChatSessionList(BaseModel):
    total: int
    sessions: list[ChatSessionOut]


class ChatMessageList(BaseModel):
    total: int
    messages: list[ChatMessageOut]


class ChatHistorySearch(BaseModel):
    query: str
