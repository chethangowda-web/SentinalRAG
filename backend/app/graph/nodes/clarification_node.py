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

    graph_execution = list(state.get("graph_execution", []))
    graph_execution.append({
        "node_name": "clarification",
        "execution_time_ms": elapsed,
        "input": f"question={question[:80]}, {len(chunks)} chunks",
        "output": f"needed={needed}" + (f": {clarification[:80]}" if clarification else ""),
        "decision": "complete -> END",
        "next_node": "END",
        "retry_count": state.get("retry_count", 0),
    })

    logger.info(
        "Clarification node: needed=%s (%.1fms)",
        needed, elapsed,
    )

    return {
        "clarification_needed": needed,
        "clarification_question": clarification,
        "latencies": latencies,
        "reasoning_path": reasoning_path,
        "graph_execution": graph_execution,
    }
