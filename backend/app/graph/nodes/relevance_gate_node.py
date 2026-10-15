import logging
import time

from app.core.config import settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

OFF_TOPIC_ANSWER = (
    "I don't have enough information to answer this question: nothing in your documents covers it. "
    "Try rephrasing, or upload a document that does."
)


def best_rerank_score(chunks: list[dict]) -> float | None:
    """Highest cross-encoder score among the retrieved passages, or None when none was scored."""
    scores = [c["rerank_score"] for c in chunks if c.get("rerank_score") is not None]
    return max(scores) if scores else None


def is_off_topic(chunks: list[dict]) -> bool:
    """True when even the best passage is judged unrelated to the question by the cross-encoder.

    Vector similarity cannot tell this: every text is "somewhat similar" to every other, so an
    unrelated question still scores a plausible 0.4. The cross-encoder is far more decisive
    (unrelated questions score about -11, relevant ones above -9).
    """
    threshold = settings.OFF_TOPIC_RERANK_THRESHOLD
    if threshold is None or not chunks:
        return False
    best = best_rerank_score(chunks)
    return best is not None and best < threshold


def relevance_gate_node(state: GraphState) -> dict:
    """End early, without any LLM call, when nothing retrieved is related to the question."""
    start = time.perf_counter()
    chunks = state.get("retrieved_chunks", [])
    off_topic = is_off_topic(chunks)
    best = best_rerank_score(chunks)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["relevance_gate_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("relevance_gate")

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "relevance_gate",
        "execution_time_ms": elapsed,
        "input": f"{len(chunks)} chunks, best rerank={'n/a' if best is None else round(best, 2)}",
        "output": "nothing related found" if off_topic else "related passages found",
        "decision": "off topic -> END" if off_topic else "related -> ambiguity_check",
        "next_node": "END" if off_topic else "ambiguity_check",
        "retry_count": state.get("retry_count", 0),
    })

    update = {"latencies": latencies, "reasoning_path": reasoning_path, "graph_execution": graph_execution}
    if off_topic:
        logger.info("Relevance gate: best rerank %.2f below %.2f, answering without the LLM", best, settings.OFF_TOPIC_RERANK_THRESHOLD)
        update.update({
            "answer": OFF_TOPIC_ANSWER,
            "citations": [],
            "confidence_score": 0.0,
            "confidence_level": "LOW",
        })
    return update


def route_after_relevance_gate(state: GraphState) -> str:
    return "end" if state.get("answer") == OFF_TOPIC_ANSWER else "ambiguity_check"
