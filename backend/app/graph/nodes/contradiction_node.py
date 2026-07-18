import logging
import time

from app.graph.state import GraphState
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

    logger.info(
        "Contradiction node: detected=%s (%s) %.1fms",
        detected, reason[:60] if reason else "none", elapsed,
    )

    return {
        "contradiction_detected": detected,
        "contradiction_reason": reason,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }


def route_after_contradiction(state: GraphState) -> str:
    if state.get("contradiction_detected"):
        logger.info("Contradiction detected -> routing to clarification")
        return "clarification"
    logger.info("No contradiction -> routing to generate_answer")
    return "generate_answer"
