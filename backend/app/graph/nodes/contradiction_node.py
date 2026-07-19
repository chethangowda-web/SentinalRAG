import logging
import time

from app.graph.state import GraphState
from app.services.confidence_service import calculate_confidence_with_breakdown
from app.services.contradiction_service import detect_contradictions

logger = logging.getLogger(__name__)


def contradiction_node(state: GraphState) -> dict:
    start = time.perf_counter()
    chunks = state.get("retrieved_chunks", [])

    detected, reason = detect_contradictions(chunks)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["contradiction_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("contradiction_detect")

    decision = f"{'detected -> clarification' if detected else 'none -> generate_answer'}"
    next_node = "clarification" if detected else "generate_answer"

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "contradiction_detect",
        "execution_time_ms": elapsed,
        "input": f"{len(chunks)} chunks",
        "output": f"detected={detected}" + (f": {reason[:80]}" if reason else ""),
        "decision": decision,
        "next_node": next_node,
        "retry_count": state.get("retry_count", 0),
    })

    vector_scores_c = [c.get("vector_score", 0) for c in chunks if c.get("vector_score")]
    rerank_scores_c = [c.get("rerank_score", 0) for c in chunks if c.get("rerank_score")]
    retry_success_c = state.get("retry_count", 0) > 0 and state.get("confidence_improved", False)
    _, contradiction_breakdown = calculate_confidence_with_breakdown(
        vector_scores=vector_scores_c,
        rerank_scores=rerank_scores_c,
        total_results=len(chunks),
        citation_count=len(chunks),
        contradiction_detected=detected,
        retry_success=retry_success_c,
    )

    logger.info(
        "Contradiction node: detected=%s (%s) %.1fms",
        detected, reason[:60] if reason else "none", elapsed,
    )

    return {
        "contradiction_detected": detected,
        "contradiction_reason": reason,
        "confidence_breakdown": contradiction_breakdown,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
    }


def route_after_contradiction(state: GraphState) -> str:
    if state.get("contradiction_detected"):
        logger.info("Contradiction detected -> routing to clarification")
        return "clarification"
    logger.info("No contradiction -> routing to generate_answer")
    return "generate_answer"
