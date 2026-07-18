import logging
import time

from app.graph.state import GraphState
from app.services.confidence_service import calculate_confidence

logger = logging.getLogger(__name__)


def confidence_node(state: GraphState) -> dict:
    start = time.perf_counter()
    chunks = state.get("retrieved_chunks", [])

    vector_scores = [c.get("vector_score", 0) for c in chunks if c.get("vector_score")]
    rerank_scores = [c.get("rerank_score", 0) for c in chunks if c.get("rerank_score")]

    conf = calculate_confidence(
        vector_scores=vector_scores,
        rerank_scores=rerank_scores,
        total_results=len(chunks),
    )

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["confidence_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("confidence_evaluate")

    reason = (
        f"Vector similarity avg: {sum(vector_scores)/len(vector_scores):.3f}" if vector_scores else "No vector scores"
    )

    logger.info(
        "Confidence node: score=%.1f level=%s (%d chunks) %.1fms",
        conf.score, conf.level, len(chunks), elapsed,
    )

    return {
        "confidence_score": conf.score,
        "confidence_level": conf.level,
        "confidence_reason": reason,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }


def route_after_confidence(state: GraphState) -> str:
    level = state.get("confidence_level", "LOW")
    if level == "HIGH":
        logger.info("Confidence HIGH -> routing to generate")
        return "generate_answer"
    logger.info("Confidence %s -> routing to rewrite", level)
    return "rewrite_query"
