from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class CitationItem(BaseModel):
    document_id: str
    chunk_id: str
    page: int | None = None
    text: str | None = None


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    confidence_level: str
    reasoning_path: list[str]
    citations: list[CitationItem]
    clarification_question: str | None = None
    latencies: dict[str, float] | None = None
    trace_id: str | None = None
