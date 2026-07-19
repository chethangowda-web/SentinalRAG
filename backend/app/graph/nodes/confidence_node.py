import logging
import time

from app.graph.state import GraphState
from app.services.confidence_service import calculate_confidence_with_breakdown

logger = logging.getLogger(__name__)


def confidence_node(state: GraphState) -> dict:
    start = time.perf_counter()
    chunks = state.get("retrieved_chunks", [])

    vector_scores = [c.get("vector_score", 0) for c in chunks if c.get("vector_score")]
    rerank_scores = [c.get("rerank_score", 0) for c in chunks if c.get("rerank_score")]
    citation_count = state.get("retrieval_details", [])
    citation_count = len([c for c in chunks if c.get("chunk_id")])
    contradiction_detected = state.get("contradiction_detected", False)
    retry_success = state.get("retry_count", 0) > 0

    conf, breakdown = calculate_confidence_with_breakdown(
        vector_scores=vector_scores,
        rerank_scores=rerank_scores,
        total_results=len(chunks),
        citation_count=citation_count,
        contradiction_detected=contradiction_detected,
        retry_success=retry_success,
    )

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["confidence_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("confidence_evaluate")

    reason = (
        f"Vector similarity avg: {sum(vector_scores)/len(vector_scores):.3f}" if vector_scores else "No vector scores"
    )

    level = conf.level
    decision = f"{level} -> {'generate_answer' if level == 'HIGH' else 'rewrite_query'}"
    next_node = "generate_answer" if level == "HIGH" else "rewrite_query"

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "confidence_evaluate",
        "execution_time_ms": elapsed,
        "input": f"{len(chunks)} chunks, scores={len(vector_scores)}vec/{len(rerank_scores)}rerank",
        "output": f"confidence={conf.score:.1f}/{conf.level}, breakdown available",
        "decision": decision,
        "next_node": next_node,
        "retry_count": state.get("retry_count", 0),
    })

    logger.info(
        "Confidence node: score=%.1f level=%s (%d chunks) %.1fms",
        conf.score, conf.level, len(chunks), elapsed,
    )

    return {
        "confidence_score": conf.score,
        "confidence_level": conf.level,
        "confidence_reason": reason,
        "confidence_breakdown": breakdown,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
    }


def route_after_confidence(state: GraphState) -> str:
    level = state.get("confidence_level", "LOW")
    if level == "HIGH":
        logger.info("Confidence HIGH -> routing to generate")
        return "generate_answer"
    logger.info("Confidence %s -> routing to rewrite", level)
    return "rewrite_query"
