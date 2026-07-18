import logging
import time

from app.graph.state import GraphState
from app.services.clarification_service import detect_ambiguity

logger = logging.getLogger(__name__)


async def clarification_node(state: GraphState) -> dict:
    start = time.perf_counter()
    question = state.get("rewritten_question") or state["question"]
    chunks = state.get("retrieved_chunks", [])

    clarification = detect_ambiguity(question, chunks)

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    latencies = dict(state.get("latencies", {}))
    latencies["clarification_node"] = elapsed

    reasoning_path = list(state.get("reasoning_path", []))
    reasoning_path.append("clarification")

    needed = clarification is not None

    logger.info(
        "Clarification node: needed=%s (%.1fms)",
        needed, elapsed,
    )

    return {
        "clarification_needed": needed,
        "clarification_question": clarification,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
    }
