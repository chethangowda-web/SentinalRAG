from typing import TypedDict


class GraphState(TypedDict):
    question: str
    rewritten_question: str | None
    retrieved_chunks: list[dict]
    confidence_score: float
    confidence_level: str
    confidence_reason: str | None
    retry_count: int
    max_retries: int
    contradiction_detected: bool
    contradiction_reason: str | None
    clarification_needed: bool
    clarification_question: str | None
    answer: str | None
    citations: list[dict]
    reasoning_path: list[str]
    latencies: dict[str, float]
