import logging
import time

from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def fallback_node(state: GraphState) -> dict:
    start = time.perf_counter()

    answer = (
        "I don't have enough evidence to answer this question reliably. "
        "Please upload additional documents or rephrase your question "
        "to be more specific."
    )

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["fallback_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("fallback_low_confidence")

    logger.info("Fallback node: returning low confidence response (%.1fms)", elapsed)

    return {
        "answer": answer,
        "citations": [],
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }
